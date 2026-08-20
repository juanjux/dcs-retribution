"""Which payload stations DCS will silently empty.

A weapon loads only if the mod DECLARES the clsid and OFFERS it on that exact pylon.
Fail either and DCS drops the store without a word: the aircraft takes off a missile
short and nothing in the log says so. This reads each installed mod's own pylon table
and checks every station of every payload the fork ships against it.

Run: python tools/audit_mod_pylons.py
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

MODS = Path.home() / "Saved Games/DCS/Mods/aircraft"
PAYLOAD_DIRS = [
    Path.home() / "Saved Games/DCS/MissionEditor/UnitPayloads",  # takes precedence
    Path("resources/customized_payloads"),
]

_BLOCK_COMMENT = re.compile(r"--\[\[.*?\]\]", re.S)
_LINE_COMMENT = re.compile(r"--[^\n]*")
_NAME = re.compile(r"""^\s*Name\s*=\s*['"]([^'"]+)['"]""", re.M)
_CLSID = re.compile(r'CLSID\s*=\s*"([^"]+)"')
_VAR_TABLE = re.compile(r"^\s*(?:local\s+)?([A-Za-z_]\w*)\s*=\s*\{", re.M)


def strip_comments(text: str) -> str:
    """A commented-out clsid is not offered, and counting it hides a real drop."""
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def balanced(text: str, start: int, opener: str = "{", closer: str = "}") -> str:
    """The text from `start` to the bracket that closes the one it opens with."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def weapon_variables(text: str) -> dict[str, set[str]]:
    """Mods list weapons once in a variable and reference it from several pylons."""
    out: dict[str, set[str]] = {}
    for m in _VAR_TABLE.finditer(text):
        body = balanced(text, m.end() - 1)
        clsids = set(_CLSID.findall(body))
        if clsids:
            out[m.group(1)] = clsids
    return out


def pylon_offers(text: str) -> dict[int, set[str]]:
    """pylon(N, ...) -> every clsid it accepts, inline or via a referenced variable."""
    variables = weapon_variables(text)
    offers: dict[int, set[str]] = collections.defaultdict(set)
    for m in re.finditer(r"\bpylon\s*\(\s*(\d+)\s*,", text):
        call = balanced(text, text.index("(", m.start()), "(", ")")
        pylon = int(m.group(1))
        for argument in split_arguments(call):
            # A variable counts only when it IS an argument. Matching any identifier
            # found anywhere inside the call unions unrelated weapon tables into every
            # pylon, which reads as "this station takes everything" and hides real
            # drops -- every Su-57 station came back with the same 43 weapons.
            if argument in variables:
                offers[pylon] |= variables[argument]
            else:
                offers[pylon] |= set(_CLSID.findall(argument))
    return dict(offers)


def split_arguments(call: str) -> list[str]:
    """The top-level arguments of a pylon(...) call, brackets respected."""
    args: list[str] = []
    depth, start = 0, 1
    for i, ch in enumerate(call):
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
            if depth == 0:
                args.append(call[start:i])
                break
        elif ch == "," and depth == 1:
            args.append(call[start:i])
            start = i + 1
    return [a.strip() for a in args]


def aircraft_names(text: str) -> set[str]:
    names = set()
    for m in re.finditer(r"DisplayName\s*=", text):
        chunk = text[max(0, m.start() - 300) : m.start() + 300]
        names |= {n for n in _NAME.findall(chunk) if "Carrier" not in n}
    return names


def installed_offers() -> dict[str, dict[int, set[str]]]:
    found: dict[str, dict[int, set[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(set)
    )
    for lua in MODS.rglob("*.lua"):
        try:
            raw = lua.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "Pylons" not in raw or "CLSID" not in raw:
            continue
        text = strip_comments(raw)
        names = aircraft_names(text)
        if not names:
            continue
        offers = pylon_offers(text)
        for name in names:
            for pylon, clsids in offers.items():
                found[name][pylon] |= clsids
    return found


def fork_payloads() -> dict[str, Path]:
    """Payloads bind by the unitType inside the file, never by its filename."""
    out: dict[str, Path] = {}
    for directory in PAYLOAD_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.lua")):
            text = path.read_text(encoding="utf-8", errors="replace")
            match = re.search(r'\["name"\] = "([^"]+)"', text)
            if match and match.group(1) not in out:
                out[match.group(1)] = path
    return out


def main() -> None:
    offers = installed_offers()
    payloads = fork_payloads()
    auditable = sorted(set(offers) & set(payloads))
    print(f"mod aircraft with a readable pylon table: {len(offers)}")
    print(f"of those, with a payload the fork ships:  {len(auditable)}\n")

    total = 0
    for unit in auditable:
        text = payloads[unit].read_text(encoding="utf-8", errors="replace")
        reported = False
        for chunk in re.split(r"\n\t\t\[\d+\] = \{", text):
            name = re.search(r'\["name"\] = "([^"]+)"', chunk)
            stations = re.findall(
                r'\["CLSID"\] = "([^"]*)",\s*\r?\n\s*\["num"\] = (\d+)', chunk
            )
            if not name or not stations:
                continue
            dropped = sorted(
                (int(num), clsid)
                for clsid, num in stations
                if clsid and clsid not in offers[unit].get(int(num), set())
            )
            if not dropped:
                continue
            if not reported:
                print(f"  {unit}")
                reported = True
            total += len(dropped)
            print(
                f"      {name.group(1):26} {len(dropped)} of {len(stations)} stations: "
                + ", ".join(f"{n} ({c})" for n, c in dropped)
            )
    print(f"\nstations DCS would silently empty: {total}")


if __name__ == "__main__":
    main()
