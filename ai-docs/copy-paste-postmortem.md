# Copy-paste transport — abandoned (post-mortem)

The OPFOR-AI feature shipped three transports: **REST**, **MCP**, and **copy-paste**
(paste a per-turn text "blob" into any chat LLM, paste its reply back). Copy-paste was
meant for free / tool-less accounts. After play-testing it across ChatGPT, Grok, Gemini,
Copilot and Claude (haiku/sonnet/opus), we removed it. REST and MCP stay.

## Why it was the wrong protocol

- **No interactivity — the decisive flaw.** The LLM gets one text dump and must emit a
  whole turn blind. It cannot ask a follow-up, and — the concrete pain — it cannot
  **evaluate a candidate package's TOT** (will this strike make the mission window?)
  before committing. REST/MCP fix this: the model calls tools, can query, and can
  dry-run (see the new `evaluate_package`).
- **No per-action feedback inside a turn.** Commands are applied in one batch; the model
  can't see "this package can't be crewed / that base can't recruit" until after it has
  committed the whole reply.
- **Obfuscation was a dead end.** base64 made *every* tier forfeit the turn (they truncate
  the hand-decode and treat it as missing data). Handle-safe ROT13 fixed the forfeits and
  the weak-model handle corruption, but it's still friction-for-friction's-sake and only a
  soft obfuscation.
- **Everything had to be spoon-fed.** Because the model couldn't query or compute, the
  blob had to pre-bake distances, naval groupings, SAM coverage, parking, front balance,
  etc. That's a lot of one-shot text instead of structured data the model can pull on
  demand. Those enrichments are being re-added to REST/MCP as **structured DTO fields** in
  `turn_context` (where the model can also request only what it needs).

What *did* work and is kept: the read context, the planner/engine reuse, the write actions
(packages, buy/sell, buy ground, stances, squadron relocate, ground transfer, delete), and
the Take-Off gate — all of it lives in REST + MCP.

## Recovering the implementation

The copy-paste code is preserved in git history, last present at commit **`d06ef9135`**
(the parent of the removal). The removal is **`4d881a5f5`** on `experiment-mcp`.

- View it: `git show d06ef9135:game/agent/copypaste.py`
  and `git show d06ef9135:qt_ui/windows/copypaste_ai_dialog.py`
- Restore it: `git checkout d06ef9135 -- game/agent/copypaste.py qt_ui/windows/copypaste_ai_dialog.py`
  (then re-add the two settings + the QTopPanel/QSettings wiring), or `git revert 4d881a5f5`.

The blob builder there is also a good reference for the engine APIs behind the new DTO
fields: distances (`position.distance_to_point`/`heading_between_point` + `utils.meters`),
naval grouping (`ship_tgo.control_point`), parking (`ParkingType` + `total_aircraft_parking`/
`unclaimed_parking`), base adjacency (`cp.connected_points`), front balance
(`cp.base.total_armor`), recruit-capable (`cp.has_ground_unit_source`).
