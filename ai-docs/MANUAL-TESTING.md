# OPFOR-AI — manual test checklist

Everything below was built on branch `experiment-mcp` and verified **headless only**
(loading saves via the venv / FastAPI `TestClient`). **Nothing is validated in the
running game yet, and the dist has NOT been rebuilt** (retribution_main.exe was open).
Work top to bottom. `chinos2` is backed up to `chinos2.retribution.20260630.bak`.

Legend: 🔴 = could break things / pay attention · ⚙️ = setup · ✅ = expected result.

---

## 0. Build / run the new code  ⚙️🔴

The new code is on `experiment-mcp` only; your current dist does **not** have it.

- [X] **Close retribution_main.exe** before rebuilding.
- [X] Make sure you're on the branch with the work: `git -C "<repo>" status` → `experiment-mcp`.
- [X] **Rebuild** with your usual full-fork process (`pyinstaller pyinstaller.spec` → `dist_full_fork`). The spec was updated to bundle `game/agent/docs/*.md` and the `mcp` + `sse_starlette` submodules.
  - 🔴 The build now pulls in **`mcp`** and bumps **`anyio` 3.7.1 → 4.14.1**. Watch the PyInstaller output for missing-module warnings about `mcp`, `sse_starlette`, `httpx`, `pydantic`. If the built exe crashes on start with an `mcp`/`anyio` import error, add the offending module to `hiddenimports` in `pyinstaller.spec` and rebuild.
  - [X] Preserve `state.json` as usual.
- [ ] **Faster alternative for testing (no rebuild):** run from source —
  `& "<repo>\.venv\Scripts\python.exe" "<repo>\qt_ui\main.py"`.
- [X] ✅ The game starts normally with the feature OFF (regression: nothing changed for normal play).

## 1. Enable the feature  ⚙️

- [X] Settings → **Campaign Management → "OPFOR AI commander"** → tick **"Allow OPFOR AI control"**. Close settings.
- [X] ✅ No crash; the setting sticks after closing/reopening settings.
- [X] Load an **old save** (e.g. the chinos2 backup). ✅ It loads (the new `stored_context` / setting back-fill is save-safe).

## 2. Find the connect URL + token, and choose REST vs MCP  ⚙️

- [ ] Settings → **Campaign Management → "OPFOR AI commander"**. With **"Allow OPFOR AI control" ON** and **Copy-Paste mode OFF**, a **"Connect your LLM"** block shows **two URLs** with **Copy** buttons:
  - **REST** (`…/retribution-ai/start?token=…`) — for Claude Code or curl.
  - **MCP** (`…/mcp?token=…`) — for claude.ai connectors or `claude mcp add`.
  - 👉 **There is no REST-vs-MCP toggle** — both are always live when the feature is on. You pick by which URL you give your client. (Answers "how do I use MCP instead of REST".)
- [ ] ✅ The **Copy-Paste mode** checkbox is **greyed out** while the master is OFF, and **auto-unchecks** if you turn the master off (so the toolbar button only shows in a real mode).
- [ ] (The URLs are also in the status window: click the **"OPFOR AI"** button in the top panel.)
- [ ] (The connect URL is still logged once at startup, but settings is the place to grab it.)

## 3. Auth  🔴

- [ ] `curl "http://[::1]:<PORT>/retribution-ai/turn_context"` (no token) → ✅ **403 Forbidden**.
- [ ] `curl "http://[::1]:<PORT>/retribution-ai/turn_context?token=<KEY>"` → ✅ **200** + JSON.
- [ ] `curl -H "X-API-Key: <KEY>" "http://[::1]:<PORT>/retribution-ai/turn_context"` → ✅ 200 (header auth works too).
- [ ] `curl "http://[::1]:<PORT>/mcp"` (no token) → ✅ **403**.

## 4. Reads (REST)  

(Use `?token=<KEY>` on each.)

- [ ] `GET /retribution-ai/start` → ✅ markdown briefing; **`{BASE_URL}` is filled in** (no literal `{BASE_URL}`), no `<!-- -->` header.
- [ ] `GET /retribution-ai/howtoplay` → ✅ briefing with **your red faction name/country filled in** (no `{RED_FACTION}`).
- [ ] `GET /retribution-ai/turn_context?side=red` → ✅ `situation`, `economy` (budget/income), `control_points` (with lat/lng + owner), `air_wing` (squadrons with ids), **`targets`** (SAMs/ships/buildings with ids + `threat_nm`). Numbers look sane vs the in-game map.
- [ ] `GET /retribution-ai/settings` → ✅ aggressiveness %, map visibility, mission-window minutes, income multipliers.
- [ ] `GET /retribution-ai/packages?side=red` → ✅ current red packages (likely **empty** if the feature is ON and you haven't planned — see §8).
- [ ] `GET /retribution-ai/prev_turns?n=3` → ✅ force totals (blue/red aircraft + vehicles) for recent turns.
- [ ] `GET /retribution-ai/turn_status` → ✅ `{active, status, cancelled, turn}`.
- [ ] 🔴 Cross-check: a target id from `turn_context.targets` matches a real SAM/ship on the map; lat/lng put bases in the right place.

## 5. Writes (REST)  🔴

- [ ] `POST /retribution-ai/packages` with body
  `{"side":"red","packages":[{"target_id":"<a target id from §4>","flights":[{"task":"DEAD","count":2}],"rationale":"test DEAD"}]}`
  → ✅ `[{"ok":true,...,"package":{...}}]`.
- [ ] `GET /packages?side=red` → ✅ the new package is there. On the **map**, red now has a package aimed at that target.
- [ ] 🔴 **Crewing:** open the red flight — ✅ it has pilots (no empty seats). At Take Off there should be **no "missing pilots"** block for red.
- [ ] Try a bad target (carrier for OCA, or a nonsense id) → ✅ `{"ok":false,"error":"..."}` (graceful, no crash).
- [ ] `POST /retribution-ai/buy/aircraft` `{"side":"red","squadron_id":"<id>","quantity":2}` → ✅ ok; **budget drops**, `pending_deliveries` +2 (check `turn_context` again or the Air Wing window).
- [ ] `POST /retribution-ai/sell/aircraft` `{"side":"red","squadron_id":"<id of a squadron with untasked aircraft>","quantity":1}` → ✅ ok; budget rises.
- [ ] `POST /retribution-ai/stances` `{"side":"red","friendly_cp_id":"<red cp>","enemy_cp_id":"<blue cp>","stance":"breakthrough"}` → ✅ ok (only meaningful where a front line connects them).
- [ ] `DELETE /retribution-ai/packages/0?side=red` → ✅ that package is gone (map updates).
- [ ] `DELETE /retribution-ai/packages?side=red` → ✅ all red packages cleared.

## 6. Take-Off gate + indicator (Qt — never tested in-game)  🔴

- [ ] `POST /retribution-ai/ai/active?active=true` → ✅ the **"OPFOR AI"** button in the **Misc** box (top panel) turns green/active and shows status.
- [ ] Click **Take Off** → ✅ a popup blocks it: *"OPFOR AI is planning…"*.
- [ ] `POST /retribution-ai/ai/status?text=Planning%20packages` → ✅ the button text updates.
- [ ] Click the **"OPFOR AI"** button → ✅ a status window opens; **"Cancel AI turn"** sets `cancelled` (check `turn_status`).
- [ ] `POST /retribution-ai/ai/active?active=false` → ✅ button goes idle; **Take Off now proceeds**.
- [ ] 🔴 With the setting OFF, the "OPFOR AI" button should be **hidden**.

## 7. Memory (stored_context + human_notes)

- [ ] `PUT /retribution-ai/stored_context` body `{"strategy":"hit the carrier group"}` → `GET /stored_context` returns it.
- [ ] `POST /retribution-ai/stored_context` `{"player":"rushes north"}` → ✅ both keys present (merge).
- [ ] `DELETE /retribution-ai/stored_context/player` → ✅ only `strategy` left.
- [ ] **Save the campaign, reload it** → ✅ `GET /stored_context` still returns `strategy` (persists in the save).
- [ ] Write something in the in-game **Notes** panel → `GET /retribution-ai/human_notes` returns it.

## 8. Autonomous wiring + scripted fallback (Phase 5 — core turn logic)  🔴🔴

- [ ] With **"Allow OPFOR AI control" ON**, advance/begin a turn (Pass Turn). Then `GET /packages?side=red` → ✅ **empty** (red's auto-planning was suppressed, left for the LLM).
- [ ] 🔴 **Fallback:** WITHOUT planning red (don't call the LLM at all), click **Take Off**. ✅ Red is **not empty** in the mission — the scripted commander filled it (a fallback log line / red flights appear). The mission should play normally with a scripted red.
- [ ] Now **plan red via the LLM** (create some packages), then Take Off → ✅ red flies **the LLM's** plan (the fallback does NOT overwrite it).
- [ ] Turn the setting **OFF**, advance a turn → ✅ red auto-plans as before (scripted), `GET /packages?side=red` is **populated**. (Regression — confirms we didn't break normal OPFOR.)
- [ ] 🔴 Confirm red still **buys/reinforces** automatically with the setting ON (procurement is intentionally NOT suppressed) — budget changes turn to turn.

## 9. MCP transport

### Claude Code (localhost, no tunnel)
- [ ] `claude mcp add --transport http "http://[::1]:<PORT>/mcp?token=<KEY>"`.
- [ ] In Claude Code, ✅ the OPFOR tools appear (`turn_context`, `create_packages`, `buy_aircraft`, `set_ai_active`, `stored_context`, …).
- [ ] Ask it to read `turn_context` and create a package → ✅ same effect as the REST writes.

### claude.ai web (needs a tunnel)  🔴
- [ ] Expose the port (e.g. `cloudflared tunnel --url http://localhost:<PORT>` or ngrok).
- [ ] Add a **custom connector** in claude.ai pointing at `https://<tunnel>/mcp?token=<KEY>`.
- [ ] ✅ Tools load; reads/writes work.
- [ ] 🔴 **Security:** the token gates `/mcp`, but keep the tunnel URL private — anyone with `…/mcp?token=<KEY>` can command red. Close the tunnel when done.

## 10. Full "play a turn against the LLM" (the real goal)

- [ ] Connector configured (REST or MCP). Tell your LLM **"your turn"**.
- [ ] ✅ It: `set_ai_active(true)` → reads `turn_context`/`prev_turns`/`stored_context` → creates packages (open SAMs with DEAD, escort strikers, anti-ship the fleet…), maybe buys/sets stances → saves a note → `set_ai_active(false)`.
- [ ] While it plans, ✅ you can keep planning blue (not blocked); **only Take Off is gated**.
- [ ] **View red's plan** (the button), sanity-check the rationales, then Take Off and fly. ✅ Red executes the LLM's plan.
- [ ] Next turn: ✅ the LLM references its `stored_context` note and `prev_turns` (reacts to losses).

## 11. Regression (the anyio 4 / mcp changes)  🔴

- [ ] The **map web view** loads and updates (the in-process server still works under anyio 4).
- [ ] A **normal mission** (feature OFF) plans, launches, and debriefs as before.
- [ ] No new errors in the log on startup/shutdown (the MCP lifespan + the server thread shut down cleanly on exit).

---

## 12. Copy-paste mode (free-LLM accounts)  🔴 (Qt, never run)

- [ ] Enable **"Allow OPFOR AI control"** (master) FIRST, then tick **"Copy-Paste mode"**
  (it's greyed out until the master is on). The top-panel **"OPFOR AI"** button turns blue:
  *"copy-paste — click to plan"*.
- [ ] Click it → ✅ the window opens and explains the flow (briefing once, then copy/paste each turn).
- [ ] **Briefing for your LLM** → ✅ a **copyable** window with a full briefing (role,
  doctrine, package composition, planning, fair play, command grammar, a worked example,
  and the base64 instructions). Paste it to your LLM **once**.
- [ ] **Copy turn blob** → it's **base64** (you see gibberish, not red's state/plan). Paste
  it to your LLM → it decodes + replies (ideally base64). Paste the reply → **Apply reply**
  → ✅ per-line results (ok/FAIL) and the map shows the new red packages.
- [ ] ✅ Works whether the LLM replied in **base64** or **plain** command lines.
- [ ] 🔴 Note: base64 is **obfuscation, not encryption** — a determined player could still
  decode it. And a weak/free LLM may struggle to decode/encode a few KB of base64 reliably.
- [ ] Leave red empty (don't apply), Take Off → ✅ the scripted fallback fills red.

## Previously-pending items, now built (validate in-game)

All headless/syntax-checked only:

- **Settings URL panel + dependency**: in the **OPFOR AI commander** section, the "Connect
  your LLM" block (REST + MCP URLs, Copy buttons) shows when the master is on + copy-paste
  off; the Copy-Paste checkbox is gated on the master (see §2). The status window also shows
  both URLs.
- **Front-line targets**: in a **land** campaign, `turn_context.targets` includes
  `kind:"front"` (suggested_task CAS) with `friendly_cp_id`/`enemy_cp_id`; `POST /packages`
  with a front id plans CAS, and the cp pair drives `/stances`. (chinos2 is naval → no
  fronts; validate with a land campaign — e.g. start a quick Syria/Caucasus one.)
- **Detailed debrief**: after a flown mission, `prev_turns` entries gain `blue_air_lost` /
  `red_air_lost` / `blue_ground_lost` / `red_ground_lost` for that turn.

## Still not done
- **Nothing is validated in a real Qt/game session yet** — all the Qt (the Take-Off
  gate/indicator §6, the settings dependency + URL block §2, the copy-paste window §12) is
  syntax/import-checked only. The dist **is** rebuilt — this is what you're testing now.

## If something is broken
- REST 500s on `/start` or `/howtoplay` in the **built exe** → the docs weren't bundled; confirm `game/agent/docs` is in `pyinstaller.spec` datas (it is) and rebuild.
- `/mcp` 404/500 in the exe → an `mcp` submodule wasn't bundled; add it to `hiddenimports`.
- Old save won't load → tell me the `KeyError`/`AttributeError`; the `stored_context`/setting back-fill should cover it, but report any other missing field.
