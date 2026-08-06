# 414th Weapon-Coverage Completion — PLAN (annotate me)

Working plan for bringing `resources/weapons/` up to the current DCS patch
(base 0.15.0 + bundled CurrentHill / mod packs) and balancing introduction dates.

**How to use this doc:** edit the `year:`/`fb:` values inline, tick `[x]` to approve a line,
change `[ ]` → `[-]` to skip/leave-in-Unknown, and write notes after the `💬`. I'll regenerate
the YAMLs from whatever this doc says once you're done.

Mechanics: each family has a `year` + `fallback`; `Loadout.degrade_for_date()` substitutes down
the fallback chain when a weapon isn't available yet. No-YAML CLSIDs land in **"Unknown"** =
always available, never degrade. Iron bombs in Unknown are harmless; guided weapons are the gap.

## ✅ COMPLETION STATUS (coverage phase done)

| Metric | Start | Now |
|---|---|---|
| CLSIDs covered | 475 | **1864** |
| Broken/stale entries | 25 | **5** (all harmless — see below) |
| Uncovered → "Unknown" | 3040 | 1638 (intended leave-set) |
| Groups | 233 | 301 |

`WeaponGroup.load_all()` loads clean (no duplicate CLSID/name), no empty groups, all 228
fallbacks resolve. **Section A applied** with two balance re-dates from review: **AIM‑120C →
2018** and **AIM‑9X → 2018** (base + `2x` groups). **Section B fold-ins applied.**

**5 remaining stale (harmless dead CLSIDs DCS removed / mod-only — left intentionally):**
`{20_x_AGM_86C}` `{6_x_AGM_86C_MER}` (B‑52 ALCM combos removed from DCS),
`{VSN-Aspide}` `{VSN_F104_LAU105_AIM9L}` `{VSN_F104_LAU105_AIM9P}` (VSN mod only).

**Minor gaps still in Unknown (optional phase-2 adds):** Chinese KD‑63 / KS‑1 / CMII, Indian
Rudra‑M1, GBU‑31 plain‑TV variants, ADM‑141A TALD variants, unguided rocket pods (LAU‑3/10/61,
B‑8M1 S‑8, B‑13L S‑13). All era-agnostic or niche — left always-available.

**Regeneration:** built from `_wpntools/spec.py` + `gen.py` (gitignored scratch). Re-run to
absorb new CLSIDs after a future DCS patch.

---

Legend: 🔵 base DCS · 🟣 mod pack. (Tables below = the applied decisions; edit for phase-2 balance.)

---

## PHASE 2 — Balance re-dates (gate best-in-class to the modern era)

Same treatment as **AIM‑120C → 2018** / **AIM‑9X → 2018**: push each class's premium weapon to
the 2018 gate so only present-day campaigns field it; the tier just below stays historical and
becomes the workhorse. Edit the `→` year, untick to skip. **Gate year = `2018`** (change globally
if you want a different "modern" line).

### Tier 1 — premium "decisive edge" → 2018  ✅ APPLIED
- [x] **R‑77** (red active BVR) — `2002` → `2018`  · keeps R‑27ER (1990) as red's workhorse BVR
  💬
- [x] **AGM‑65K** (newest Maverick, CCD) — `2008` → `2018`  · keeps AGM‑65D/G
  💬
- [x] **AGM‑154C JSOW** (unitary BROACH) — `2005` → `2018`  · keeps JSOW‑A (1998)
  💬
- [x] **GBU‑54B LJDAM** (laser+GPS) — `2012` → `2018`  · keeps GBU‑38 JDAM (2002)
  💬
- [x] **GBU‑39 SDB** — `2006` → `2018`
  💬
- [x] **KAB‑500S** (Russian GPS) — `2007` → `2018`  · keeps KAB‑500Kr/LG
  💬
- [x] **AGM‑114L Longbow** (mmW fire-&-forget) — `2000` → `2018`  · keeps AGM‑114K (1993)
  💬

### Tier 2 — more aggressive (optional, default skip)
- [ ] **AGM‑84H SLAM‑ER** — `2000` → `2018`  · keeps SLAM (1990)
  💬
- [ ] **Storm Shadow** — `2003` → `2018` · **Taurus KEPD‑350** — `2005` → `2018`
  💬
- [ ] **Kh‑101** — `2012` → `2018`  · keeps Kh‑555 (2004)
  💬
- [x] **TGPs — left historical, NO 2018 gate** ✅ (per SME tiering: **LITENING = ATFLIR > Sniper/ATP**).
  The best pods (LITENING 1999, ATFLIR 2003) are the *baseline service kit*, not a gateable edge —
  and AAQ‑33 Sniper is the *lesser* pod, so gating it would make the weakest pod the rarest
  (backwards). There is no premium pod sitting above the baseline, so the whole TGP ladder stays at
  its historical dates. (AAQ‑33 reverted 2018 → 2005.)

### Flag — RESOLVED
- [x] **AGM‑154B JSOW** left at `2030` (disabled). Per SME: only JSOW **A and C** are in the
  game; **B is not flyable**, so it stays parked. (A=1998 workhorse, C=2018 premium.)

---

## A. NEW families — approve / edit year + fallback

### A1. A2A missiles
- [ ] **AIM-120D AMRAAM** — year: `2008` — fb: `AIM-120C` · 🔵 mostly AI-only, pre-2020
  💬I want the Aim120c dated something like 2018, aim 120d should fall into the post 2020
- [ ] **R-37 (AA-13 Axehead)** — year: `2014` — fb: `R-77` · 🔵 MiG-31, low use
  💬
- [ ] **R-37M (AA-13)** — year: `2019` — fb: `R-37` · 🔵 low use
  💬
- [ ] **FIM-92 Stinger (A2A)** — year: `1982` — fb: `—` · 🔵 helo self-defense
  💬
- [ ] **9M39 Igla (A2A)** — year: `1983` — fb: `—` · 🔵 helo self-defense
  💬

### A2. Anti-ship missiles
- [ ] **Kh-22 (AS-4 Kitchen)** — year: `1962` — fb: `—` · 🔵 Tu-22M
  💬
- [ ] **Kh-22MA** — year: `1975` — fb: `Kh-22` · 🔵
  💬
- [ ] **Kh-22P (passive/anti-radar)** — year: `1968` — fb: `Kh-22` · 🔵 type ARM
  💬
- [ ] **Kh-41 Moskit (SS-N-22 Sunburn)** — year: `1984` — fb: `Kh-22` · 🔵
  💬
- [ ] **AM39 Exocet** — year: `1979` — fb: `—` · 🔵 Super Étendard / Mirage
  💬
- [ ] **Kormoran** — year: `1977` — fb: `—` · 🟣 German Tornado
  💬
- [ ] **Sea Eagle** — year: `1985` — fb: `—` · 🟣 UK
  💬
- [ ] **KSR-2 (AS-5 Kelt)** — year: `1962` — fb: `—` · 🟣 Tu-16
  💬
- [ ] **KSR-5 (AS-6 Kingfish)** — year: `1969` — fb: `KSR-2` · 🟣
  💬
- [ ] **KSR-2P / KSR-5P (passive)** — year: `1966` / `1973` — fb: `KSR-2` / `KSR-5` · 🟣 ARM
  💬
- [ ] **RB-04E** — year: `1975` — fb: `—` · 🟣 Swedish Viggen
  💬
- [ ] **RB-15F** — year: `1989` — fb: `RB-04E` · 🟣 Swedish Viggen
  💬
- [ ] **RBS-15 Mk4** — year: `2017` — fb: `RB-15F` · 🟣 post-2017, low use
  💬
- [ ] **C-802AK** — year: `1998` — fb: `—` · 🟣 Chinese
  💬
- [ ] **YJ-83K** — year: `2010` — fb: `C-802AK` · 🟣 Chinese
  💬
- [ ] **YJ-12** — year: `2015` — fb: `—` · 🟣 Chinese, low use
  💬
- [ ] **CM-802AKG** — year: `2012` — fb: `—` · 🟣 Chinese TV
  💬
- [ ] **CM-400AKG** — year: `2012` — fb: `—` · 🟣 Chinese hypersonic
  💬
- [ ] **BrahMos (A-Ship / SEAD)** — year: `2006` — fb: `—` · 🟣 Indian Su-30
  💬

### A3. Land-attack cruise / ALCM
- [ ] **Kh-20 (AS-3 Kangaroo)** — year: `1960` — fb: `—` · 🟣 Tu-95
  💬
- [ ] **Kh-555** — year: `2004` — fb: `Kh-65` · 🔵
  💬
- [ ] **Kh-101** — year: `2012` — fb: `Kh-555` · 🔵
  💬
- [ ] **Storm Shadow** — year: `2003` — fb: `—` · 🟣 Tornado/Typhoon
  💬
- [ ] **Taurus KEPD-350** — year: `2005` — fb: `—` · 🟣 Tornado
  💬
- [ ] **KD-20** — year: `2008` — fb: `—` · 🟣 Chinese H-6K
  💬
- [ ] **AGM-158B JASSM-ER** — year: `2014` — fb: `AGM-154C JSOW` · 🔵 low use
  💬
- [ ] **AGM-158C LRASM** — year: `2018` — fb: `—` · 🔵 low use
  💬

### A4. PGM / glide / TV-guided
- [ ] **GBU-8/B HOBOS** — year: `1969` — fb: `GBU-10` · 🔵 early EO
  💬
- [ ] **GBU-15 (V1 / (V)1/B / (V)31/B)** — year: `1983` — fb: `GBU-10` · 🔵
  💬
- [ ] **AGM-130** — year: `1994` — fb: `GBU-15` · 🔵 powered GBU-15
  💬
- [ ] **AGM-142 Popeye** — year: `1989` — fb: `GBU-15` · 🟣 F-15I/F-4
  💬
- [ ] **GBU-39 SDB** — year: `2006` — fb: `GBU-38` · 🔵
  💬
- [ ] **JDAM-ER (GPS Mk-83)** — year: `2015` — fb: `GBU-32(V)2/B` · 🔵 low use
  💬
- [ ] **GB-6 / GB-6-HE / GB-6-SFW** — year: `2010` — fb: `—` · 🟣 Chinese glide
  💬
- [ ] **LS-6 (250 / 500)** — year: `2010` — fb: `—` · 🟣 Chinese JDAM-like
  💬
- [ ] **DWS39 / BK-90 Mjölner** — year: `1995` — fb: `—` · 🟣 Swedish dispenser
  💬

### A5. Cluster / dispenser / incendiary
- [ ] **CBU-52B** — year: `1970` — fb: `Mk 82` · 🔵
  💬
- [ ] **CBU-1/A, CBU-2/A, CBU-2B/A (BLU-3/4)** — year: `1965` — fb: `Mk 82` · 🔵 Vietnam
  💬
- [ ] **Mk-77 mod 1 (fire bomb)** — year: `1970` — fb: `—` · 🔵 napalm
  💬
- [ ] **BL-755** — year: `1973` — fb: `Mk 82` · 🟣 UK
  💬
- [ ] **BLG-66 Belouga (AC / EG)** — year: `1979` — fb: `Mk 82` · 🟣 French
  💬
- [ ] **RBK-250** — year: `1960` — fb: `FAB-250 M62` · 🔵 Soviet
  💬
- [ ] **RBK-500-255** — year: `1975` — fb: `FAB-500 M62` · 🔵 Soviet
  💬
- [ ] **KMGU-2** — year: `1980` — fb: `RBK-250` · 🔵 Soviet dispenser
  💬

### A6. GP bombs not yet covered
- [ ] **FAB-100** — year: `1946` — fb: `—` · 🔵 Soviet light GP
  💬
- [ ] **OFAB-100-120** — year: `1980` — fb: `FAB-100` · 🔵
  💬
- [ ] **OFAB-250-270** — year: `1962` — fb: `FAB-250 M62` · 🔵
  💬
- [ ] **SAMP-125 / 250 / 400** — year: `1970` — fb: `—` · 🟣 French
  💬
- [ ] **BR-250 / BR-500** — year: `1970` — fb: `—` · 🟣 French
  💬
- [ ] **BAP-100 (anti-runway)** — year: `1983` — fb: `—` · 🟣 French
  💬
- [ ] **BAT-120** — year: `1980` — fb: `—` · 🟣 French frag
  💬
- [ ] **SB M/71 (120 kg HD/LD)** — year: `1971` — fb: `—` · 🟣 Swedish Viggen
  💬

### A7. Helo ATGM
- [ ] **9M114 Shturm (AT-6)** — year: `1978` — fb: `—` · 🔵 Mi-24
  💬
- [ ] **9M120 Ataka (AT-9) (+9M120F/9M220O)** — year: `1996` — fb: `9M114 Shturm` · 🔵
  💬
- [ ] **HOT-3** — year: `1998` — fb: `—` · 🟣 Gazelle
  💬
- [ ] **Spike-ER** — year: `2004` — fb: `—` · 🟣
  💬
- [ ] **Brimstone** — year: `2005` — fb: `AGM-114K` · 🟣 UK
  💬

### A8. Russian standoff (new variants)
- [ ] **Kh-59MK2 (AS-22 Kazoo)** — year: `2010` — fb: `Kh-59M` · 🔵
  💬
- [ ] **Kh-36 / Grom-E1 (AS-23)** — year: `2015` — fb: `Kh-29T` · 🟣 low use
  💬

---

## B. Fold uncovered variants into EXISTING dated groups — no year decision

Per-aircraft / rack / sub-variant CLSIDs of already-dated families; they inherit the existing
group's year. Tick to confirm, or 💬 to carve any out as its own dated family instead.

- [ ] **LGB:** GBU-10, GBU-12, GBU-16, GBU-24, GBU-31(V)1/2/3/4, GBU-32(V)2/B, GBU-38, GBU-54B
  💬
- [ ] **Maverick:** AGM-65D/E/F/G/H/K (LAU-88 triples etc.)
  💬
- [ ] **Harpoon/SLAM:** AGM-84D, AGM-84E SLAM, AGM-84H SLAM-ER
  💬
- [ ] **JSOW:** AGM-154A, AGM-154C
  💬
- [ ] **AMRAAM:** AIM-120B, AIM-120C per-pylon LAU-127 variants
  💬
- [ ] **CBU:** CBU-87, CBU-97, CBU-103, CBU-105 rack variants
  💬
- [ ] **KAB:** KAB-1500Kr, KAB-1500LG-Pr
  💬
- [ ] **Russian standoff:** Kh-29L/T (+KH-29TE TV), Kh-31A/P (+AD/PD), Kh-35 (+UE), Kh-59M (+MK)
  💬
- [ ] **ARM:** AGM-78 Standard ARM (plain), AGM-45A variant
  💬
- [ ] **Rockets:** S-25/O-25, B-8M1 (S-8), B-13L (S-13), LAU-3/10/61 pods
  💬
- [ ] **BLU-107 Durandal** (new group, year `1977`, fb `—`, or fold if you prefer)
  💬
- [ ] **Decoy:** ADM-141A TALD variants (existing 1987)
  💬
- [ ] **AGM-86C:** repoint dead 20x/6x files to `{8_x_AGM_86C}`
  💬

---

## C. Proposed to LEAVE in "Unknown" (always-available) — flip to `[x]` to date instead

- [ ] **Nuclear:** RDS-37, B-43, B-28, Mk.53, RN-24/28/244, GAM-63 RASCAL, ASM-N-2 Bat
  💬
- [ ] **Super-heavy / niche:** GBU-43 MOAB, GBU-57 MOP, FAB-3000 / FAB-9000 M54
  💬
- [ ] **WWII GP bombs:** AN-M57/64/65/66/81/88, SC/SD 250/500, 250/500 lb GP Mk, Tiny Tim, HVAR, RP-3
  💬
- [ ] **Post-2020 bleeding edge:** Meteor, AIM-260, AGM-88G AARGM-ER, AIM-174B
  💬
- [-] **Training / inert / torpedoes / FLIR-nav / decoy-only one-offs** — never dated
  💬

---

## Global questions
1. 💬 Mod-pack AShM/ALCM with no clean predecessor — OK to leave `fallback` empty (they vanish
   before their year rather than degrading)? ok
2. 💬 Nuclear + WWII bombs — leave in Unknown, or date them? unknown
3. 💬 Anything here you'd rather split or merge differently? Not really besides the aim 120 comment
