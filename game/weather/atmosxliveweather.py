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
from math import ceil, floor
from pathlib import Path
from typing import Any, Optional

from dcs.cloud_presets import CLOUD_PRESETS
from dcs.weather import CloudPreset, Weather, Wind

from game.utils import meters, mm_hg
from game.weather.atmosphericconditions import AtmosphericConditions
from game.weather.clouds import Clouds
from game.weather.fog import Fog
from game.weather.weather import Weather as GameWeather
from game.weather.weatherarchetype import WeatherArchetype, WeatherArchetypes
from game.weather.wind import WindConditions

CLI_NAME = "atmosx-cli.exe"
ICAO_CSV = "dcs_icao.csv"

# An ICAO location indicator: exactly four letters, never digits or dashes.
_ICAO = re.compile(r"[A-Za-z]{4}")

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
                icao = row[2].strip()
                # A third of the Syria rows are DCS's own identifiers for airfields
                # with no observing station -- OS57, SY-U-A, IQ-0018. An ICAO location
                # indicator is four letters, and the CLI rejects anything else, so
                # keeping them only risks the fallback picking one.
                if not _ICAO.fullmatch(icao):
                    continue
                out.append(Station(icao.upper(), row[1].strip()))
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


def _cloud_preset(key: Any) -> Optional[CloudPreset]:
    """The pydcs preset the observation names, if this DCS install has it."""
    if not isinstance(key, str) or not key or key == "none":
        return None
    entry = CLOUD_PRESETS.get(key)
    if entry is None:
        logging.warning("ATMOS-X live weather: unknown cloud preset %s", key)
        return None
    return entry.value


def read_clouds(
    vdata: dict[str, Any],
) -> Optional[tuple[Optional[CloudPreset], int, int, int, int]]:
    """The observation's cloud layer as (preset, base, thickness, density, iprecptns).

    None when the sky is clear -- no preset and nothing to draw. The base is clamped to
    the preset's own range: DCS refuses to save a mission whose base falls outside it,
    and a METAR ceiling a few metres below a preset's minimum is not worth a crash.
    """
    clouds = vdata.get("clouds")
    if not isinstance(clouds, dict):
        return None
    preset = _cloud_preset(clouds.get("preset"))
    base = int(round(float(clouds.get("base", 0))))
    thickness = int(round(float(clouds.get("thickness", 0))))
    density = int(round(float(clouds.get("density", 0))))
    if preset is None and not density and not thickness:
        return None
    if preset is not None:
        clamped = min(max(base, ceil(preset.min_base)), floor(preset.max_base))
        if clamped != base:
            logging.info(
                "ATMOS-X live weather: cloud base %dm clamped to %dm for %s",
                base,
                clamped,
                preset.name,
            )
            base = clamped
    try:
        precipitation = int(round(float(clouds.get("iprecptns", 0))))
    except (TypeError, ValueError):
        precipitation = 0
    return preset, base, thickness, density, precipitation


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

    layer = read_clouds(vdata)
    if layer is None:
        # A clear METAR is a real answer, not "leave the campaign's clouds alone".
        weather.clouds_preset = None
        weather.clouds_base = 0
        weather.clouds_thickness = 0
        weather.clouds_density = 0
        weather.clouds_iprecptns = Weather.Preceptions.None_
    else:
        preset, base, thickness, density, precipitation = layer
        # clouds_preset must be the pydcs object: the mission writer reads .name off it
        # and validates the base against it, so the preset key as a bare string would
        # take mission generation down.
        weather.clouds_preset = preset
        weather.clouds_base = base
        weather.clouds_thickness = thickness
        weather.clouds_density = density
        try:
            # DCS models precipitation as an enum, not a scale: anything the preset
            # reports that is not rain or thunderstorm is "none" rather than a guess.
            weather.clouds_iprecptns = Weather.Preceptions(precipitation)
        except ValueError:
            weather.clouds_iprecptns = Weather.Preceptions.None_

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


def player_base_names(theater: Any) -> list[str]:
    """The player's airfields, to favour a station they will actually fly from.

    Deliberately the STARTING coalition rather than the current owner. The turn's
    weather is decided in ``Game.__init__``, which runs while a new campaign is still
    being generated: the control points exist but have not been handed to a coalition
    yet, so asking which are the player's raises there -- and a new campaign would then
    have no airfield to prefer at all and fall back to picking a station by position.
    Starting ownership is known from the moment the theater is loaded.

    It is also the steadier input: the observing station should not move to another
    airfield mid-campaign because a base changed hands.
    """
    names = []
    for control_point in getattr(theater, "controlpoints", []):
        coalition = getattr(control_point, "starting_coalition", None)
        if coalition is not None and coalition.is_blue:
            names.append(control_point.name)
    return names


def fetch_observation(
    theater: Any, settings: Any
) -> Optional[tuple[str, dict[str, Any]]]:
    """The current observation for this campaign's terrain, or None with a reason logged.

    Every way this can fail returns None: the campaign must still be playable with the
    weather Retribution generates when ATMOS-X is absent, the network is down, or the
    station reported nothing.
    """
    from game.settings.settings import CloudPresetPack

    if not settings.atmosx_live_weather:
        return None
    if settings.cloud_preset_pack is not CloudPresetPack.ATMOSX:
        logging.warning(
            "ATMOS-X live weather is on but the cloud preset pack is %s; skipping. The "
            "observation's cloud preset only means what ATMOS-X says it means.",
            settings.cloud_preset_pack.value,
        )
        return None

    configured = (settings.atmosx_cli_path or "").strip()
    cli = Path(configured) if configured else detect_cli()
    if cli is None or not cli.is_file():
        logging.warning(
            "ATMOS-X live weather: %s not found; keeping the generated weather.",
            configured or CLI_NAME,
        )
        return None

    icao = (settings.atmosx_metar_station or "").strip().upper()
    if not icao:
        bases = player_base_names(theater)
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
            return None
        icao = station.icao

    preset = fetch_preset(cli, icao)
    if preset is None or "vdata" not in preset:
        return None
    return icao, preset["vdata"]


# --- the observation as the game's own weather ------------------------------------


class LiveWeather(GameWeather):
    """A real observation, in the shape the rest of the game already understands.

    Retribution decides a turn's weather when the turn begins, and the turn display,
    the kneeboards, the active-runway choice and the carrier's course into wind all read
    that decision -- so the observation has to *be* the turn's weather, not something
    grafted onto the .miz at the end. What the model cannot hold (visibility distance,
    dust) stays in ``vdata``, which the mission generator writes out as well.
    """

    def __init__(self, station: str, vdata: dict[str, Any]) -> None:
        self.station = station
        self.vdata = vdata
        # Deliberately not calling super().__init__(): every field it would randomise
        # is an observed fact here, and it wants seasonal data this does not need.
        self.atmospheric = self._atmospheric()
        self.clouds = self._clouds()
        self.fog = self._fog()
        self.wind = self._wind()

    @property
    def archetype(self) -> WeatherArchetype:
        """Only used for random wind, which this never does -- but it must be sane."""
        precipitation = 0
        clouds = self.vdata.get("clouds")
        if isinstance(clouds, dict):
            precipitation = int(float(clouds.get("iprecptns", 0) or 0))
        if precipitation >= 2:
            return WeatherArchetypes.with_id("thunderstorm")
        if precipitation == 1:
            return WeatherArchetypes.with_id("raining")
        if self.clouds is not None:
            return WeatherArchetypes.with_id("cloudy")
        return WeatherArchetypes.with_id("clear")

    def _atmospheric(self) -> AtmosphericConditions:
        season = self.vdata.get("season")
        temperature = 20.0
        if isinstance(season, dict) and "temperature" in season:
            temperature = float(season["temperature"])
        return AtmosphericConditions(
            qnh=mm_hg(float(self.vdata.get("qnh", 760.0))),
            temperature_celsius=temperature,
            turbulence_per_10cm=float(self.vdata.get("groundTurbulence", 0.0)),
        )

    def _clouds(self) -> Optional[Clouds]:
        layer = read_clouds(self.vdata)
        if layer is None:
            # A clear METAR: nothing to draw. "No clouds" is what the rest of the game
            # reads as clear, and it is what the observation means.
            return None
        preset, base, thickness, density, precipitation = layer
        try:
            reported = Weather.Preceptions(precipitation)
        except ValueError:
            reported = Weather.Preceptions.None_
        return Clouds(
            base=base,
            density=density,
            thickness=thickness,
            precipitation=reported,
            preset=preset,
        )

    def _fog(self) -> Optional[Fog]:
        """Only the legacy fog block maps onto the model; fog2 rides along in vdata."""
        fog = self.vdata.get("fog")
        if not isinstance(fog, dict) or not self.vdata.get("enable_fog"):
            return None
        return Fog(
            visibility=meters(float(fog.get("visibility", 0))),
            thickness=int(round(float(fog.get("thickness", 0)))),
        )

    def _wind(self) -> WindConditions:
        wind = self.vdata.get("wind")
        wind = wind if isinstance(wind, dict) else {}
        return WindConditions(
            at_0m=_wind(wind.get("atGround")) or Wind(),
            at_2000m=_wind(wind.get("at2000")) or Wind(),
            at_8000m=_wind(wind.get("at8000")) or Wind(),
        )


def live_weather_for(theater: Any, settings: Any) -> Optional[LiveWeather]:
    """This turn's weather, taken from the sky rather than from the dice."""
    observation = fetch_observation(theater, settings)
    if observation is None:
        return None
    station, vdata = observation
    try:
        weather = LiveWeather(station, vdata)
    except (KeyError, TypeError, ValueError):
        logging.exception("ATMOS-X live weather: unusable observation for %s", station)
        return None
    logging.info("ATMOS-X live weather: %s applied (campaign clock kept)", station)
    return weather


def refresh_live_weather(game: Any) -> bool:
    """Replace this turn's weather with a newly fetched observation.

    For the player who planned at dawn and takes off at noon, or whose first attempt
    found no network. Returns False and leaves the turn alone if nothing came back.
    """
    weather = live_weather_for(game.theater, game.settings)
    if weather is None:
        return False
    game.conditions.weather = weather
    return True


def live_weather_enabled(settings: Any) -> bool:
    """Whether asking for an observation is worth offering at all."""
    from game.settings.settings import CloudPresetPack

    return bool(
        settings.atmosx_live_weather
        and settings.cloud_preset_pack is CloudPresetPack.ATMOSX
    )
