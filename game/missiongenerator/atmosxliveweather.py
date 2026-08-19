"""Real-world weather for a generated mission, via the ATMOS-X CLI.

ATMOS-X ships ``atmosx-cli.exe``, which fetches a METAR for an ICAO station and writes
a DCS weather preset. We use its read-only ``metar --save`` rather than its ``inject``
command: ``inject`` always stamps the mission's date and time as well, and a campaign
set in 2030 must be able to take today's weather without being dragged back to today's
date. The saved preset keeps the two apart -- ``vdata`` is the weather, ``dtime`` is the
clock -- and we take only ``vdata``.

Nothing here is allowed to stop a mission being generated. Every failure (no CLI, no
network, an ICAO with no observation, a malformed file) logs and returns, leaving the
weather Retribution had already generated.
"""

from __future__ import annotations

import csv
import logging
import re
import subprocess
import tempfile
import unicodedata
import winreg
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dcs.mission import Mission
from dcs.weather import Weather, Wind

CLI_NAME = "atmosx-cli.exe"
ICAO_CSV = "dcs_icao.csv"

_UNINSTALL_KEYS = (
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
)


def detect_cli() -> Optional[Path]:
    """The installed atmosx-cli.exe, found through the installer's registry entry.

    Matched on the display name rather than the product GUID: the GUID is an
    implementation detail of one installer build, the name is not.
    """
    for hive, path in _UNINSTALL_KEYS:
        try:
            with winreg.OpenKey(hive, path) as root:
                for i in range(winreg.QueryInfoKey(root)[0]):
                    try:
                        with winreg.OpenKey(root, winreg.EnumKey(root, i)) as key:
                            name, _ = winreg.QueryValueEx(key, "DisplayName")
                            if "ATMOS-X" not in str(name):
                                continue
                            location, _ = winreg.QueryValueEx(key, "InstallLocation")
                    except OSError:
                        continue
                    candidate = Path(str(location)) / CLI_NAME
                    if candidate.is_file():
                        return candidate
        except OSError:
            continue
    return None


# --- the preset file -------------------------------------------------------------
#
# A small reader for the subset of Lua the CLI emits: top-level `name = { ... }`
# assignments of nested tables holding numbers, strings and booleans. pydcs' own lua
# parser rejects the file (it is a script, not a bare table), and a regex over nested
# tables would break the first time a field moves, so parse it properly.

_TOKEN = re.compile(
    r"""
    (?P<comment>--[^\n]*)
  | (?P<space>\s+)
  | (?P<string>"(?:[^"\\]|\\.)*")
  | (?P<number>-?\d+\.?\d*(?:[eE][-+]?\d+)?)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<punct>[{}\[\]=,;])
    """,
    re.VERBOSE,
)


class PresetParseError(RuntimeError):
    pass


def _tokenize(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pos = 0
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if match is None:
            raise PresetParseError(f"unexpected character at offset {pos}")
        pos = match.end()
        kind = match.lastgroup
        assert kind is not None
        if kind in ("space", "comment"):
            continue
        out.append((kind, match.group()))
    return out


def parse_preset(text: str) -> dict[str, Any]:
    """The top-level assignments of an ATMOS-X preset file, as nested dicts."""
    tokens = _tokenize(text)
    index = 0

    def peek() -> Optional[tuple[str, str]]:
        return tokens[index] if index < len(tokens) else None

    def expect(value: str) -> None:
        nonlocal index
        token = peek()
        if token is None or token[1] != value:
            raise PresetParseError(f"expected {value!r}, found {token!r}")
        index += 1

    def value() -> Any:
        nonlocal index
        token = peek()
        if token is None:
            raise PresetParseError("unexpected end of file")
        kind, raw = token
        if raw == "{":
            return table()
        index += 1
        if kind == "number":
            return float(raw) if ("." in raw or "e" in raw.lower()) else int(raw)
        if kind == "string":
            return raw[1:-1]
        if raw == "true":
            return True
        if raw == "false":
            return False
        if raw == "nil":
            return None
        raise PresetParseError(f"unexpected token {raw!r}")

    def table() -> dict[str, Any]:
        nonlocal index
        expect("{")
        out: dict[str, Any] = {}
        while True:
            token = peek()
            if token is None:
                raise PresetParseError("unterminated table")
            if token[1] == "}":
                index += 1
                return out
            if token[1] == "[":
                index += 1
                key = str(value())
                expect("]")
            else:
                key = token[1]
                index += 1
            expect("=")
            out[key] = value()
            token = peek()
            if token is not None and token[1] in (",", ";"):
                index += 1

    result: dict[str, Any] = {}
    while index < len(tokens):
        kind, raw = tokens[index]
        if kind != "name":
            raise PresetParseError(f"expected an assignment, found {raw!r}")
        index += 1
        expect("=")
        result[raw] = value()
    return result


# --- station selection -----------------------------------------------------------


def _fold(name: str) -> str:
    """Airfield names as written by ED and by ATMOS-X differ in accents and suffixes."""
    folded = unicodedata.normalize("NFKD", name)
    folded = "".join(c for c in folded if not unicodedata.combining(c)).lower()
    for junk in (" air base", " airbase", " international", " airport", "-", "'", "."):
        folded = folded.replace(junk, " ")
    return " ".join(folded.split())


@dataclass(frozen=True)
class Station:
    icao: str
    airfield: str


def stations_for_theater(cli: Path, theater_name: str) -> list[Station]:
    """The ICAO stations ATMOS-X knows for a terrain, from the CSV beside the CLI."""
    csv_path = cli.parent / ICAO_CSV
    if not csv_path.is_file():
        logging.warning("ATMOS-X live weather: %s not found next to the CLI", ICAO_CSV)
        return []
    wanted = _fold(theater_name)
    out: list[Station] = []
    try:
        with csv_path.open(encoding="utf-8-sig", errors="replace") as handle:
            for row in csv.reader(handle):
                if len(row) < 3 or not row[2].strip():
                    continue
                if _fold(row[0]) != wanted:
                    continue
                out.append(Station(row[2].strip(), row[1].strip()))
    except OSError as exc:
        logging.warning("ATMOS-X live weather: cannot read %s: %s", csv_path, exc)
    return out


def choose_station(
    cli: Path,
    theater_name: str,
    preferred_airfields: list[str],
    positions: Optional[dict[str, Any]] = None,
) -> Optional[Station]:
    """The station to ask for, favouring an airfield the player actually flies from.

    ED and ATMOS-X spell the same airfield differently often enough that matching them
    verbatim finds almost nothing (two of sixty on Syria), so names are folded first.
    When nothing matches -- ATMOS-X only lists airfields with a real observing station,
    so most bases will not -- fall back to the nearest station that does, rather than
    give up or take an arbitrary one: on the same map, a real observation a hundred
    kilometres away still describes the weather far better than no observation at all.

    ``positions`` maps airfield name to a point with ``x``/``y``, normally the terrain's
    airports. Without it the fallback is simply the first station listed.
    """
    stations = stations_for_theater(cli, theater_name)
    if not stations:
        return None
    by_name = {_fold(s.airfield): s for s in stations}
    for airfield in preferred_airfields:
        station = by_name.get(_fold(airfield))
        if station is not None:
            return station

    if positions:
        folded_positions = {_fold(name): p for name, p in positions.items()}
        origin = next(
            (
                folded_positions[_fold(a)]
                for a in preferred_airfields
                if _fold(a) in folded_positions
            ),
            None,
        )
        if origin is not None:
            located = [
                (s, folded_positions[_fold(s.airfield)])
                for s in stations
                if _fold(s.airfield) in folded_positions
            ]
            if located:
                return min(
                    located,
                    key=lambda pair: (pair[1].x - origin.x) ** 2
                    + (pair[1].y - origin.y) ** 2,
                )[0]
    return stations[0]


# --- fetching and applying -------------------------------------------------------


def fetch_preset(cli: Path, icao: str, timeout: int = 60) -> Optional[dict[str, Any]]:
    """Run the CLI's read-only metar command and parse what it saves.

    Always the current observation. The CLI's --date only reaches 30 days back, which
    no campaign's own date can be counted on to fall inside, so the mission keeps its
    own clock and takes today's real sky.
    """
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "atmosx_live.lua"
        command = [str(cli), "metar", icao, "--save", str(out)]
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logging.warning("ATMOS-X live weather: %s failed: %s", CLI_NAME, exc)
            return None
        if result.returncode != 0 or not out.is_file():
            logging.warning(
                "ATMOS-X live weather: no observation for %s (%s)",
                icao,
                (result.stdout or result.stderr or "").strip()[:200],
            )
            return None
        try:
            return parse_preset(out.read_text(encoding="utf-8", errors="replace"))
        except (OSError, PresetParseError) as exc:
            logging.warning("ATMOS-X live weather: unreadable preset: %s", exc)
            return None


def _wind(data: Any) -> Optional[Wind]:
    if not isinstance(data, dict):
        return None
    return Wind(int(round(float(data.get("dir", 0)))), float(data.get("speed", 0)))


def apply_weather(weather: Weather, vdata: dict[str, Any]) -> None:
    """Copy the observation onto the mission's weather, field by field.

    Deliberately not a wholesale replacement: the preset carries only what a METAR
    describes, and anything it leaves out (dust, halo, cyclones) should keep whatever
    the campaign chose rather than be reset to a default.
    """
    if "qnh" in vdata:
        weather.qnh = int(round(float(vdata["qnh"])))
    season = vdata.get("season")
    if isinstance(season, dict) and "temperature" in season:
        weather.season_temperature = float(season["temperature"])
    if "groundTurbulence" in vdata:
        weather.turbulence_at_ground = int(round(float(vdata["groundTurbulence"])))
    visibility = vdata.get("visibility")
    if isinstance(visibility, dict) and "distance" in visibility:
        weather.visibility_distance = int(round(float(visibility["distance"])))

    clouds = vdata.get("clouds")
    if isinstance(clouds, dict):
        weather.clouds_base = int(round(float(clouds.get("base", weather.clouds_base))))
        weather.clouds_thickness = int(
            round(float(clouds.get("thickness", weather.clouds_thickness)))
        )
        weather.clouds_density = int(
            round(float(clouds.get("density", weather.clouds_density)))
        )
        if "iprecptns" in clouds:
            # DCS models precipitation as an enum, not a scale: anything the preset
            # reports that is not rain or thunderstorm is "none" rather than a guess.
            try:
                weather.clouds_iprecptns = Weather.Preceptions(
                    int(round(float(clouds["iprecptns"])))
                )
            except ValueError:
                weather.clouds_iprecptns = Weather.Preceptions.None_
        # "none" is a real answer -- a METAR reporting no significant cloud -- so it is
        # copied across as-is rather than treated as "leave the campaign's clouds".
        weather.clouds_preset = clouds.get("preset") or None

    wind = vdata.get("wind")
    if isinstance(wind, dict):
        for key, attribute in (
            ("atGround", "wind_at_ground"),
            ("at2000", "wind_at_2000"),
            ("at8000", "wind_at_8000"),
        ):
            parsed = _wind(wind.get(key))
            if parsed is not None:
                setattr(weather, attribute, parsed)

    if "enable_dust" in vdata:
        weather.enable_dust = bool(vdata["enable_dust"])
    if "dust_density" in vdata:
        weather.dust_density = int(round(float(vdata["dust_density"])))


def apply_live_weather(mission: Mission, game: Any, mission_time: datetime) -> bool:
    """Overwrite the mission's weather with a real observation. True if it happened.

    Every way this can fail is a warning and a False, never an exception: the campaign
    must still be flyable with the weather Retribution generated when ATMOS-X is absent,
    the network is down, or the station reported nothing.
    """
    from game.settings.settings import CloudPresetPack

    settings = game.settings
    if not settings.atmosx_live_weather:
        return False
    if settings.cloud_preset_pack is not CloudPresetPack.ATMOSX:
        logging.warning(
            "ATMOS-X live weather is on but the cloud preset pack is %s; skipping. The "
            "observation's cloud preset only means what ATMOS-X says it means.",
            settings.cloud_preset_pack.value,
        )
        return False

    configured = (settings.atmosx_cli_path or "").strip()
    cli = Path(configured) if configured else detect_cli()
    if cli is None or not cli.is_file():
        logging.warning(
            "ATMOS-X live weather: %s not found; keeping the generated weather.",
            configured or CLI_NAME,
        )
        return False

    theater = game.theater
    icao = (settings.atmosx_metar_station or "").strip().upper()
    if not icao:
        bases = [cp.name for cp in theater.player_points()]
        positions = {}
        try:
            positions = {a.name: a.position for a in theater.terrain.airport_list()}
        except Exception:  # pragma: no cover - terrain data is not worth failing over
            pass
        station = choose_station(cli, theater.terrain.name, bases, positions)
        if station is None:
            logging.warning(
                "ATMOS-X live weather: no station known for %s; keeping the generated "
                "weather.",
                theater.terrain.name,
            )
            return False
        icao = station.icao

    preset = fetch_preset(cli, icao)
    if preset is None or "vdata" not in preset:
        return False

    apply_weather(mission.weather, preset["vdata"])
    logging.info("ATMOS-X live weather: %s applied (campaign clock kept)", icao)
    return True
