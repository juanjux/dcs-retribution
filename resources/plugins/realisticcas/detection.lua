-- Incremental spatial search. All engine reads are injected; no global scan.
assert(RealisticCAS and RealisticCAS.Sensors, "load core.lua and sensors.lua first")
do
  local S=RealisticCAS.Sensors
  function RealisticCAS.newDetection(options)
    local o=options or {}
    for _,name in ipairs({"clock","readObserver","readTarget","environment","lineOfSight","reveal"}) do
      assert(type(o[name])=="function",name.." callback required")
    end
    local cellSize=o.cellSize or 5000
    assert(S.finite(cellSize) and cellSize>=1000 and cellSize<=50000,"invalid cell size")
    local targetBudget=o.targetBudget or 64
    local workBudget=o.workBudget or 128
    for _,n in ipairs({targetBudget,workBudget}) do
      assert(S.finite(n) and n>=1 and n<=4096 and n==math.floor(n),"invalid work budget")
    end
    local revisit=o.revisit or 5
    assert(S.finite(revisit) and revisit>=1 and revisit<=300,"invalid revisit")
    -- Zero retains the isolated sensor-probe contract. Campaign integration will
    -- explicitly enable search time; one unknown group can occupy each observer.
    local acquisition=o.acquisitionSeconds or 0
    assert(S.finite(acquisition) and acquisition>=0 and acquisition<=600,"invalid acquisition time")
    local maxGap=o.acquisitionMaxGap or math.max(60,revisit*2)
    assert(S.finite(maxGap) and maxGap>=revisit and maxGap<=3600,"invalid acquisition observation gap")
    if acquisition>0 then assert(type(o.isRevealed)=="function","contact visibility callback required") end
    local targets, observers, cells, membership={},{},{},{}
    local targetCursor,observerCursor=1,1
    local job,enabled=nil,true
    local stats={targetReads=0,observerReads=0,candidates=0,los=0,reveals=0,errors=0,work=0,sweeps=0,
      rejectedEnvelope=0,blockedLOS=0,acquisitionStarts=0,acquisitionCompletions=0,
      acquisitionResets=0,pendingAcquisitions=0}
    local api={}
    local function log(kind,detail)
      if o.log then pcall(o.log,kind,detail) end
    end
    local function trace(kind,observer,id,target,detail)
      if not o.traceDecisions then return end
      local a,b=observer.point,target.point
      log(kind,string.format("%s -> %s|a=%.2f,%.2f,%.2f|b=%.2f,%.2f,%.2f|%s",
        job.observer.id,id,a.x,a.y,a.z,b.x,b.y,b.z,detail))
    end
    local function call(name,...)
      local ok,result=pcall(o[name],...)
      if not ok then stats.errors=stats.errors+1;log("ERROR",name..": "..tostring(result));return nil end
      return result
    end
    local function resetFocus(v,reason)
      if not v.focus then return end
      stats.pendingAcquisitions=stats.pendingAcquisitions-1
      stats.acquisitionResets=stats.acquisitionResets+1
      log("SEARCH_RESET",v.id.." -> "..v.focus.group.."|"..reason)
      v.focus=nil
    end
    local function acquired(v,target,now)
      if acquisition==0 then return true end
      local id=target.groupName or target.name
      assert(type(id)=="string","acquisition requires a target group/name")
      local f=v.focus
      if f and f.group~=id then return false end
      if f and now-f.last>maxGap then
        resetFocus(v,"observation gap");f=nil
      end
      if not f then
        f={group=id,last=now,progress=0,sweep=v.sweep}
        v.focus=f;stats.pendingAcquisitions=stats.pendingAcquisitions+1
        stats.acquisitionStarts=stats.acquisitionStarts+1
        log("SEARCH_START",v.id.." -> "..id.."|required="..acquisition)
        return false
      end
      -- Seeing ten members in one sweep is one group observation, not ten
      -- samples of search time. Scheduler stalls never count as continuous eyes-on.
      if f.sweep~=v.sweep then
        f.progress=f.progress+math.min(now-f.last,revisit)
        f.last=now;f.sweep=v.sweep
      end
      if f.progress<acquisition then return false end
      return true
    end
    local function key(x,z) return x..":"..z end
    local function unlink(id)
      local m=membership[id]
      if not m then return end
      local bucket=cells[m.key]
      local last=table.remove(bucket)
      if m.index<=#bucket then bucket[m.index]=last;membership[last].index=m.index end
      if #bucket==0 then cells[m.key]=nil end
      membership[id]=nil
    end
    local function locate(id,p)
      local k=key(math.floor(p.x/cellSize),math.floor(p.z/cellSize))
      if membership[id] and membership[id].key==k then return end
      unlink(id)
      cells[k]=cells[k] or {};local bucket=cells[k]
      bucket[#bucket+1]=id;membership[id]={key=k,index=#bucket}
    end
    function api:addTarget(id)
      assert(type(id)=="string" and id~="","target unit name required")
      for _,name in ipairs(targets) do if name==id then return false end end
      targets[#targets+1]=id;return true
    end
    function api:addObserver(id,profile)
      assert(type(id)=="string" and id~="" and type(profile)=="table","observer and profile required")
      assert(S.finite(S.maxRange(profile)) and S.maxRange(profile)<=100000,"unsupported range")
      for _,v in ipairs(observers) do if v.id==id then return false end end
      observers[#observers+1]={id=id,profile=profile,nextVisit=0,sweep=0};return true
    end
    function api:stop()
      enabled=false;job=nil;cells={};membership={}
      for _,v in ipairs(observers) do v.focus=nil end
      stats.pendingAcquisitions=0
    end
    function api:tick()
      if not enabled then return end
      local now=o.clock();assert(S.finite(now),"invalid clock")
      -- Each index refresh is bounded. Stale entries can delay a discovery, but
      -- candidates are re-read before every reveal: never publish stale truth.
      for _=1,math.min(targetBudget,#targets) do
        local id=targets[targetCursor];targetCursor=targetCursor%#targets+1
        stats.targetReads=stats.targetReads+1
        local t=call("readTarget",id)
        if t and S.vector(t.point) then locate(id,t.point) else unlink(id) end
      end
      if not job and #observers>0 then
        -- Inspect at most one observer per tick, even if all are inactive/dead.
        local v=observers[observerCursor];observerCursor=observerCursor%#observers+1
        if now>=v.nextVisit then
          stats.observerReads=stats.observerReads+1
          local snapshot=call("readObserver",v.id)
          if snapshot and S.vector(snapshot.point) then
            v.sweep=v.sweep+1
            local r=S.maxRange(v.profile)
            job={observer=v, minX=math.floor((snapshot.point.x-r)/cellSize),
              maxX=math.floor((snapshot.point.x+r)/cellSize),
              minZ=math.floor((snapshot.point.z-r)/cellSize),
              maxZ=math.floor((snapshot.point.z+r)/cellSize), seen={}}
            job.x,job.z,job.item=job.minX,job.minZ,1
          else resetFocus(v,"observer unavailable");v.nextVisit=now+revisit end
        end
      end
      if not job then return end
      stats.observerReads=stats.observerReads+1
      local observer=call("readObserver",job.observer.id)
      if not observer or not S.vector(observer.point) then
        resetFocus(job.observer,"observer unavailable");job=nil;return
      end
      local used=0
      while job and used<workBudget do
        used=used+1;stats.work=stats.work+1
        local bucket=cells[key(job.x,job.z)]
        local id=bucket and bucket[job.item]
        if id then
          job.item=job.item+1
          if not job.seen[id] then
            job.seen[id]=true;stats.candidates=stats.candidates+1
            stats.targetReads=stats.targetReads+1
            local target=call("readTarget",id)
            if target and target.side~=observer.side and S.vector(target.point) then
              local env=call("environment",observer,target,now)
              local result,reason=S.assess(observer,target,env,job.observer.profile)
              if result then
                local v=job.observer
                local known=acquisition>0 and call("isRevealed",target,observer)==true
                local group=target.groupName or target.name
                if known and v.focus and v.focus.group==group then resetFocus(v,"shared contact") end
                -- Other unknown groups wait while this observer examines one.
                -- Already shared contacts may still be observed/renewed normally.
                local available=acquisition==0 or known or not v.focus or v.focus.group==group
                if available then
                stats.los=stats.los+1
                if call("lineOfSight",observer.point,target.point)==true then
                  trace("LOS_CLEAR",observer,id,target,result.mode.."|distance="..result.distance)
                  if (known or acquired(v,target,now)) and call("reveal",target,observer,result)==true then
                    if acquisition>0 and not known then
                      stats.acquisitionCompletions=stats.acquisitionCompletions+1
                      stats.pendingAcquisitions=stats.pendingAcquisitions-1
                      v.focus=nil
                      log("SEARCH_COMPLETE",v.id.." -> "..group)
                    end
                    stats.reveals=stats.reveals+1
                    log("DETECT",job.observer.id.." -> "..id.." via "..result.mode)
                  end
                else
                  stats.blockedLOS=stats.blockedLOS+1
                  trace("LOS_BLOCKED",observer,id,target,result.mode.."|distance="..result.distance)
                end
                end
              else
                stats.rejectedEnvelope=stats.rejectedEnvelope+1
                trace("ENVELOPE_REJECT",observer,id,target,tostring(reason))
              end
            end
          end
        else
          job.item=1;job.z=job.z+1
          if job.z>job.maxZ then job.z=job.minZ;job.x=job.x+1 end
          if job.x>job.maxX then
            local v=job.observer
            if v.focus and v.focus.sweep~=v.sweep then resetFocus(v,"no valid observation this sweep") end
            job.observer.nextVisit=now+revisit;job=nil;stats.sweeps=stats.sweeps+1
          end
        end
      end
    end
    function api:getDiagnostics()
      local d={enabled=enabled,targets=#targets,observers=#observers,searching=job~=nil}
      for k,v in pairs(stats) do d[k]=v end
      return d
    end
    return api
  end
end
