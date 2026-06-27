# 05 — Headless Bootstrap & Save Format

How to construct a usable `Game` outside the Qt app, and the save format the MCP
reads/writes.

## Can it run headless? Yes.

None of `game/game.py`, `game/persistency.py`, `game/migrator.py`, or the
`game.sim` load chain import PySide/Qt. A `Game` can be loaded and planned in a
plain Python process. The only Qt-coupled bits are the UI (`qt_ui/`) and the
`QtContext`/`QtCallbacks` action bridge in the server — none of which the planner
needs.

## The bootstrap sequence

The Qt app does a lot of setup in `qt_ui/main.py` before a `Game` is usable. A
headless MCP must replicate the **non-Qt** parts. Distilled from `main.py:471`
(`main`) and `:283` (`create_game`):

```python
# 1. Logging (writes ./logs/, needs resources/default_logging.yaml; run from repo root)
from game import logging_config, VERSION
logging_config.init_logging(VERSION)

# 2. pydcs data: mods + livery cache (needed for unit/airframe class resolution)
from pydcs_extensions import load_mods
from dcs.liveries.liverycache import LiveryCache
load_mods()
LiveryCache.cache()

# 3. Persistency root (Saved Games folder). MUST happen before any *_dir() helper.
#    Qt does this inside qt_ui/liberation_install.init(); headless, call setup() directly:
from game import persistency
persistency.setup(<user_folder>, prefer_liberation_payloads=False, port=<port>)   # persistency.py:298

# 4. Custom payloads (so loadout checks / next-turn work). Replicate inject_custom_payloads:
from dcs.payloads import PayloadDirectories
PayloadDirectories.set_fallback(<repo>/resources/customized_payloads)
PayloadDirectories.set_preferred(persistency.base_path()/"MissionEditor"/"UnitPayloads")

# 5a. Load an existing save:
game = persistency.load_game(path)                 # persistency.py:417  (pickle + MigrationUnpickler)
from game.migrator import Migrator
Migrator(game, is_liberation=".liberation" in path)  # migrator.py:28  ← MUST be called separately

# 5b. …or generate a new campaign (see create_game, main.py:283): Campaign.from_file →
#     campaign.load_theater → GameGenerator(...).generate() → game.begin_turn_0(...)
```

> ⚠️ **`load_game` does NOT run the `Migrator`.** The Qt window calls it
> separately (`qt_ui/windows/QLiberationWindow.py:363-373`). Headless code must do
> both, or older saves load missing attributes and crash later. `is_liberation` is
> detected purely by `".liberation" in path`.

Wrap all of this in a single `game/agent/bootstrap.py` helper — **no such headless
bootstrapper exists today** (the Qt window is the only caller that does all the
steps). This helper is a prerequisite for Option A.

### What can break headless

- **Run from the repo root.** `init_logging` writes `./logs/`, the stylesheet/
  resources and `resources/<terrain>/landmap.p` (reloaded on unpickle by
  `ConflictTheater.__setstate__`, `conflicttheater.py:50`) are resolved relative
  to cwd.
- **pydcs + mods importable.** Unpickling resolves unit classes; if
  `pydcs_extensions` mods aren't loaded, `find_class` can raise.
- **Don't import `qt_ui.liberation_install`** to find saves — it's a Qt module and
  reads GUI-written prefs. Locate saves yourself (glob `persistency.save_dir()`).
- **`load_game` swallows all exceptions** and returns `None` with a logged
  "Invalid Save game" (`persistency.py:423`). You get no detail — if you need the
  real error, call the `MigrationUnpickler` directly or inspect `./logs/`.

## Save format

- **Plain Python `pickle`** (binary, default protocol). No JSON, no jsonpickle.
  **No version header inside the save.** Extensions: `.retribution` (current),
  `.liberation` (legacy, still loadable).
- The pickled object is the **entire `Game`** graph: theater (control points,
  ground objects, IADS), blue/red/neutral `Coalition` (faction, ATO, air wing,
  transfers, budget), `GameDb` (uuid-keyed flight/front-line/tgo registries),
  settings, weather, stats, turn, `savepath`.
- `save_game(game)` (`persistency.py:428`) writes `tmpsave.retribution` then
  `shutil.copy` to `game.savepath` — **`savepath` must be set first** (load sets
  it; for a new path set it manually). `autosave(game)` (`:454`) writes the fixed
  autosave path.
- Before pickling, `_unload_static_data()` nulls `theater.landmap` and
  `_restore_static_data()` restores it (`:442-451`) to keep saves small; landmap is
  regenerated from `resources/` on load anyway.

### Save gotchas that matter for the MCP

- **Trust:** unpickling runs `MigrationUnpickler.find_class` (arbitrary class
  resolution). **Only load trusted saves.** Surface this in the tool docs.
- **One `Game` per process.** `Game.__setstate__ → on_load()` (`game.py:170/249`)
  rebuilds derived state and mutates **process-global** singletons:
  `game.naming.namegen` is swapped, `ObjectiveDistanceCache` and theater globals
  are set. Loading a second save in the same process clobbers the first. Policy:
  one game per server process; switch saves by restarting or via a subprocess.
- **Volatile state is recomputed, not stored.** `threat_zone`, `navmesh`, `faker`
  are excluded from the pickle and rebuilt on load (`coalition.py:101-124`). After
  you mutate units, call `compute_threat_zones(events)` before re-reading threats
  or planning.
- **Transient flight state.** `Flight.state` (FlightState) is not pickled and is
  reset to `Uninitialized` on load (`flight.py:167`). Plan at turn boundaries, not
  mid-sim.
- **No partial/delta save.** It's whole-`Game` pickle only. Mutate the in-memory
  objects, then `save_game`.

## Pickle protocol / Python version

`save_game` uses pickle's default protocol (5 on modern CPython). Confirm the
desktop build's Python matches the one that wrote the saves so unpickle is
cross-compatible; the project targets the version in `requirements.txt` /
`pyinstaller.spec`.
