"""Copy-paste transport for free-LLM accounts (no API / no MCP).

In copy-paste mode the LLM has ONLY the one-time briefing plus each turn's blob —
it cannot call any read/action endpoint — so the briefing is a COMPLETE,
self-contained reference (blob format + every action) and the blob carries
everything the LLM needs (incl. the settings and the buyable ground units).

The turn data is obfuscated (opfor_ai_copy_paste_rot13, on by default) with handle-safe
ROT13 — words are ROT13'd but the handles and numbers stay plain — so the player can't
read red's state/plan at a glance while an LLM decodes it in its head WITHOUT corrupting
the load-bearing handles (plain ROT13 made weak models swap the T#/G# namespaces; base64
made every model forfeit the turn). Untick the setting for plain text. The reply is
accepted plain, handle-safe ROT13, full ROT13, or (legacy) base64. Objects use short
handles (B# base, S# squadron, T# target, G# buyable ground unit), deterministic within
a turn.
"""

from __future__ import annotations

import base64
import codecs
import re

from game.ato.flighttype import FlightType
from game.utils import meters
from game.agent import service, views

_COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def _nm(a, b) -> int:
    """Rounded nautical-mile distance between two world positions."""
    return round(meters(a.distance_to_point(b)).nautical_miles)


def _bearing(frm, to) -> str:
    """8-point compass direction from one position to another."""
    try:
        h = frm.heading_between_point(to) % 360
        return _COMPASS[int((h + 22.5) % 360 // 45)]
    except Exception:
        return "?"


# Tasks worth surfacing per squadron in the flyable summary (a pkg flight task).
_ROLE_TASKS = (
    FlightType.DEAD,
    FlightType.SEAD,
    FlightType.STRIKE,
    FlightType.CAS,
    FlightType.OCA_AIRCRAFT,
    FlightType.OCA_RUNWAY,
    FlightType.ANTISHIP,
    FlightType.BARCAP,
    FlightType.TARCAP,
    FlightType.ESCORT,
    FlightType.SWEEP,
    FlightType.AEWC,
    FlightType.REFUELING,
    FlightType.EWAR,
)


def _rot13(text: str) -> str:
    """ROT13 is its own inverse — used for both encode and decode."""
    return codecs.encode(text, "rot_13")


# Handle tokens (B5, S13, T229, G2) — kept verbatim so weak models can't corrupt them.
_HANDLE_RE = re.compile(r"(\b[BSTG]\d+\b)")


def _handle_safe_rot13(text: str) -> str:
    """ROT13 only the words, leaving handle tokens and digits in plain — even
    haiku-class models then never garble the load-bearing B#/S#/T#/G# handles
    (plain ROT13 made them swap the T#/G# namespaces). Its own inverse."""
    return "".join(
        part if _HANDLE_RE.fullmatch(part) else _rot13(part)
        for part in _HANDLE_RE.split(text)
    )


def _capable_tasks(sq) -> list[str]:
    out = []
    for ft in _ROLE_TASKS:
        try:
            if sq.capable_of(ft):
                out.append(ft.name)
        except Exception:
            pass
    return out


def _parking(cp):
    """(used, total) aircraft-parking at a base, or None if it has no slots. Lets the
    LLM see where it can station/buy aircraft (a full base has no room)."""
    from game.theater import ParkingType

    try:
        allp = ParkingType(fixed_wing=True, fixed_wing_stol=True, rotary_wing=True)
        total = cp.total_aircraft_parking(allp)
        if total <= 0:
            return None
        return total - cp.unclaimed_parking(allp), total
    except Exception:
        return None


def _looks_like_commands(text: str) -> bool:
    return bool(re.search(r"(?im)^\s*(pkg|buyg|buy|sell|stance|note|clear)\b", text))


def _build_handles(game, side: str):
    """Deterministic handle -> object maps (identical for outgoing and incoming)."""
    coalition = views.coalition_for_side(game, side)
    bases = {f"B{i}": cp for i, cp in enumerate(game.theater.controlpoints)}
    squadrons = {
        f"S{i}": sq for i, sq in enumerate(coalition.air_wing.iter_squadrons())
    }
    targets = {f"T{i}": t for i, t in enumerate(views.build_targets(game, side))}
    ground = {
        f"G{i}": gv for i, gv in enumerate(views.build_buyable_ground(game, side))
    }
    return bases, squadrons, targets, ground


def _operational_picture(game, side, bases, targets) -> list[str]:
    """Engine-generated strategic geography: where the enemy fleet is, which long-range
    SAMs gate ingress, and the distances from your launch bases to the key objectives —
    so the LLM can do OPERATIONAL planning (which base hits what) without raw coords."""
    player = views.player_for_side(side)
    cps = list(game.theater.controlpoints)
    handle_of_cp = {str(cp.id): h for h, cp in bases.items()}

    pos_by_id = {str(cp.id): cp.position for cp in cps}
    for cp in cps:
        for tgo in cp.ground_objects:
            pos_by_id[str(tgo.id)] = tgo.position
    for fr in game.theater.conflicts():
        pos_by_id[str(fr.id)] = fr.position

    red_bases = [cp for cp in cps if cp.captured == player]
    enemy_bases = [cp for cp in cps if cp.captured != player and not cp.is_fleet]
    enemy_fleets = [cp for cp in cps if cp.is_fleet and cp.captured != player]
    launch = [
        cp
        for cp in red_bases
        if any(cp.squadrons) or cp.is_fleet or cp.cptype.name == "AIRBASE"
    ]

    def near_red(pos):
        return min(
            red_bases, key=lambda b: pos.distance_to_point(b.position), default=None
        )

    out: list[str] = [
        "",
        "OPERATIONAL PICTURE (the map the engine sees — plan around it)",
    ]
    terrain = getattr(getattr(game.theater, "terrain", None), "name", None) or type(
        game.theater
    ).__name__.replace("Theater", "")
    start = game.conditions.start_time
    out.append(
        f"Theater: {terrain}. Turn starts {start:%H:%M} local "
        f"({views.build_situation(game).time_of_day})."
    )

    if enemy_fleets:
        out.append("Enemy naval groups (mobile — strike or avoid):")
        for cp in enemy_fleets:
            b = near_red(cp.position)
            where = (
                f" — {_nm(cp.position, b.position)}nm {_bearing(b.position, cp.position)} "
                f"of {handle_of_cp[str(b.id)]} {b.name}"
                if b
                else ""
            )
            out.append(f"  {handle_of_cp[str(cp.id)]} {cp.name}{where}")

    sams = sorted(
        (
            (h, t)
            for h, t in targets.items()
            if t.kind == "sam" and (t.threat_nm or 0) >= 15
        ),
        key=lambda x: -(x[1].threat_nm or 0),
    )
    if sams:
        out.append("Long-range SAM rings (route around, or DEAD first):")
        for h, t in sams[:8]:
            p = pos_by_id.get(t.id)
            b = near_red(p) if p else None
            where = (
                f" — {_nm(p, b.position)}nm {_bearing(b.position, p)} of {handle_of_cp[str(b.id)]}"
                if (p and b)
                else ""
            )
            out.append(f"  {h} {t.name} ({t.threat_nm}nm){where}")

    fronts = [(h, t) for h, t in targets.items() if t.kind == "front"]
    ships = [(h, t) for h, t in targets.items() if t.kind == "ship"]
    if launch:
        out.append("Distances from your launch bases (nm to key objectives):")
        for cp in launch:
            parts: list[str] = []
            eb = (
                min(
                    enemy_bases, key=lambda b: cp.position.distance_to_point(b.position)
                )
                if enemy_bases
                else None
            )
            if eb:
                parts.append(
                    f"enemy base {handle_of_cp[str(eb.id)]} {_nm(cp.position, eb.position)}"
                )
            for h, t in fronts[:4]:
                p = pos_by_id.get(t.id)
                if p:
                    parts.append(f"front {h} {_nm(cp.position, p)}")
            for cpf in enemy_fleets[:3]:
                parts.append(
                    f"{handle_of_cp[str(cpf.id)]} {_nm(cp.position, cpf.position)}"
                )
            for h, t in ships[:2]:
                p = pos_by_id.get(t.id)
                if p:
                    parts.append(f"{h} {_nm(cp.position, p)}")
            if parts:
                out.append(
                    f"  {handle_of_cp[str(cp.id)]} {cp.name}: " + " | ".join(parts)
                )
    return out


def _plain_outgoing(side: str) -> str:
    """The readable compact turn snapshot (before optional ROT13)."""
    game = service._require_game()
    player = views.player_for_side(side)
    tc = views.build_turn_context(game, side)
    pkgs = views.build_packages(game, side)
    st = views.build_settings(game)
    bases, squadrons, targets, ground = _build_handles(game, side)
    handle_by_cp = {str(cp.id): h for h, cp in bases.items()}

    s, e = tc.situation, tc.economy
    out = [
        f"OPFOR TURN {s.turn} — you command RED. {s.date} {s.time_of_day}."
        + (f" [{s.campaign_state}]" if s.campaign_state else ""),
        f"ECONOMY: budget {e.budget}, income/turn {e.income_next_turn}.",
    ]

    # Force balance + last-turn losses (so 'read the previous result' is satisfiable).
    try:
        prev = views.build_prev_turns(game, 1)
        if prev:
            f = prev[-1]
            out.append(
                f"FORCES: you RED ~{f.red_aircraft} aircraft / {f.red_vehicles} vehicles "
                f"vs BLUE ~{f.blue_aircraft} / {f.blue_vehicles}."
            )
            if f.red_air_lost or f.blue_air_lost or f.red_ground_lost:
                out.append(
                    f"LAST TURN losses — red air {f.red_air_lost or 0}, red ground "
                    f"{f.red_ground_lost or 0}; blue air {f.blue_air_lost or 0}, blue "
                    f"ground {f.blue_ground_lost or 0}."
                )
    except Exception:
        pass

    out.append(
        f"SETTINGS: aggressiveness {st.opfor_aggressiveness_pct}% (higher = take more "
        f"risk vs enemy SAMs) | mission window {st.desired_player_mission_duration_min} "
        f"min (every package's time-over-target is auto-set within this window of the "
        f"turn start) | map visibility {st.map_coalition_visibility} | income multiplier "
        f"you/enemy {st.player_income_multiplier}/{st.enemy_income_multiplier}."
    )
    try:
        out += _operational_picture(game, side, bases, targets)
    except Exception:
        pass
    out += [
        "",
        "GRAMMAR — reply with these commands, ONE PER LINE:",
        "  pkg <T#|enemyB#> <TASK[:count]> [<TASK[:count]> ...]   (create an air package)",
        "  buy <S#> <n>   sell <S#> <n>   buyg <yourB#> <G#> <n>   (buy/sell aircraft; buy ground)",
        "  move <S#> <yourB#>   (relocate a squadron)   movg <fromB#> <toB#> <G#> <n> [air]   (transfer ground units)",
        "  stance <yourB#> <enemyB#> <stance>   del <#index>   clear   note <key>=<text>",
        "  tasks: DEAD SEAD STRIKE CAS OCA_AIRCRAFT OCA_RUNWAY ANTISHIP BARCAP TARCAP "
        "ESCORT SWEEP AEWC REFUELING EWAR",
        "  stances: defend hold aggressive push breakthrough eliminate retreat ambush",
        "",
        "FLYABLE NOW — aircraft you can task THIS turn (pkg auto-crews from these; "
        "one airframe flies one flight):",
    ]
    flyable = [
        (h, sq)
        for h, sq in squadrons.items()
        if sq.untasked_aircraft > 0 and sq.location.captured == player
    ]
    if flyable:
        for h, sq in flyable:
            bh = handle_by_cp.get(str(sq.location.id), "?")
            caps = _capable_tasks(sq)
            captxt = (
                " ".join(caps)
                if caps
                else "transport/logistics only — cannot be tasked via pkg"
            )
            out.append(
                f"  {h} | {sq.untasked_aircraft}x {sq.aircraft.display_name} | "
                f"{bh} {sq.location.name} | can: {captxt}"
            )
    else:
        out.append(
            "  (none — every squadron owns 0 or is grounded; buy into a squadron, "
            "it arrives NEXT turn)"
        )

    out += [
        "",
        "BASES (handle | name | type | owner | #squadrons) — yours = owner red",
    ]
    for h, cp in bases.items():
        sqns = sum(1 for _ in cp.squadrons)
        out.append(
            f"{h} | {cp.name} | {cp.cptype.name} | {cp.captured.value.lower()} | {sqns}"
        )
    out += [
        "",
        "SQUADRONS (handle | aircraft | base | owned | untasked | pilots | buy-cost | "
        "note). owned 0 = no airframes (buy into it; arrives next turn).",
    ]
    for h, sq in squadrons.items():
        bh = handle_by_cp.get(str(sq.location.id), "?")
        price = getattr(sq.aircraft, "price", "?")
        note = ""
        if sq.location.captured != player:
            note = " | GROUNDED: base is enemy-held — can't fly or buy into"
        out.append(
            f"{h} | {sq.aircraft.display_name} | {bh} {sq.location.name} | "
            f"{sq.owned_aircraft} | {sq.untasked_aircraft} | "
            f"{sq.number_of_available_pilots} | buy {price}{note}"
        )

    park_lines = []
    for h, cp in bases.items():
        if cp.captured != player:
            continue
        p = _parking(cp)
        if p:
            used, total = p
            park_lines.append(
                f"{h} {cp.name}: {used}/{total} used, {total - used} free"
            )
    if park_lines:
        out += [
            "",
            "YOUR PARKING (aircraft slots per base — you can't buy/station beyond the "
            "free slots; a full base needs aircraft moved or sold first)",
        ]
        out += park_lines

    out += [
        "",
        "TARGETS — enemy objects you can attack (handle | name | kind | task | info). "
        "SAM threat <=2nm = inert/short-range (skip SEAD); plan DEAD only for >=4nm.",
    ]
    for h, t in targets.items():
        if t.kind == "front":
            fh = handle_by_cp.get(t.friendly_cp_id or "", "?")
            eh = handle_by_cp.get(t.enemy_cp_id or "", "?")
            info = f"your {fh} vs enemy {eh} (stance: stance {fh} {eh} <stance>)"
        elif t.kind == "sam":
            if not t.threat_nm:
                info = "threat unknown/destroyed"
            elif t.threat_nm <= 2:
                info = f"threat {t.threat_nm}nm (inert — skip)"
            else:
                info = f"threat {t.threat_nm}nm"
        else:
            info = f"threat {t.threat_nm}nm" if t.threat_nm else "-"
        out.append(f"{h} | {t.name} | {t.kind} | {t.suggested_task} | {info}")
    out += [
        "",
        "GROUND UNITS YOU CAN BUY (handle | name | price | kind) — buyg at a RED base "
        "with a factory/front",
    ]
    for h, gv in ground.items():
        out.append(f"{h} | {gv.name} | {gv.price} | {gv.kind}")

    name_to_gh = {gv.name: h for h, gv in ground.items()}
    red_armor = [
        (h, cp)
        for h, cp in bases.items()
        if cp.captured == player and getattr(getattr(cp, "base", None), "armor", None)
    ]
    if red_armor:
        out += [
            "",
            "YOUR GROUND FORCES (base | units on hand — move them with movg)",
        ]
        for h, cp in red_armor:
            units = ", ".join(
                f"{n}x {ut.display_name}"
                + (
                    f" ({name_to_gh[ut.display_name]})"
                    if ut.display_name in name_to_gh
                    else ""
                )
                for ut, n in cp.base.armor.items()
                if n
            )
            if units:
                out.append(f"{h} {cp.name}: {units}")

    out += [
        "",
        "CURRENT RED PACKAGES — already planned this turn (index | target | task | tot | "
        "aircraft used). Their aircraft are ALREADY removed from FLYABLE NOW; del to undo.",
    ]
    for p in pkgs:
        used = "; ".join(f"{f.count}x {f.aircraft}" for f in p.flights) or "-"
        out.append(f"#{p.index} | {p.target} | {p.task} | {p.tot or '?'} | {used}")
    return "\n".join(out)


def outgoing_blob(side: str = "red") -> str:
    """The turn snapshot, handle-safe-ROT13-obfuscated when enabled (a chat LLM decodes
    it in its head, handles intact) or plain when not — base64 is gone: hand-decoding
    it made every LLM forfeit the turn."""
    plain = _plain_outgoing(side)
    game = service._require_game()
    if getattr(game.settings, "opfor_ai_copy_paste_rot13", True):
        return _handle_safe_rot13(plain)
    return plain


def _maybe_decode(text: str) -> str:
    """Accept the reply as plain, handle-safe ROT13, full ROT13, or (legacy) base64 —
    pick whichever yields our command grammar, else treat it as plain."""
    if _looks_like_commands(text):
        return text
    for decoder in (_handle_safe_rot13, _rot13):
        candidate = decoder(text)
        if _looks_like_commands(candidate):
            return candidate
    stripped = "".join(text.split())  # base64 ignores whitespace; commands don't
    try:
        decoded = base64.b64decode(stripped, validate=True).decode("utf-8")
        if _looks_like_commands(decoded):
            return decoded
    except Exception:
        pass
    return text


def apply_incoming(side: str, text: str) -> str:
    """Parse + execute the LLM's response commands; return a result blob."""
    game = service._require_game()
    bases, squadrons, targets, ground = _build_handles(game, side)
    results: list[str] = []

    def target_id(handle: str) -> str:
        if handle in targets:
            return targets[handle].id
        if handle in bases:
            return str(bases[handle].id)
        raise ValueError(f"unknown target handle {handle!r}")

    for raw in _maybe_decode(text).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.lower() == "done":
            continue
        parts = line.split()
        cmd = parts[0].lower()
        try:
            if cmd == "pkg":
                tid = target_id(parts[1])
                flights = []
                for token in parts[2:]:
                    task, _, count = token.partition(":")
                    flights.append({"task": task, "count": int(count) if count else 2})
                res = service.create_packages(
                    side,
                    [{"target_id": tid, "flights": flights, "rationale": "copy-paste"}],
                )[0]
                results.append(
                    f"pkg {parts[1]}: " + ("ok" if res.ok else f"FAIL {res.error}")
                )
            elif cmd in ("buy", "sell"):
                sq = squadrons[parts[1]]
                qty = int(parts[2]) if len(parts) > 2 else 1
                fn = service.buy_aircraft if cmd == "buy" else service.sell_aircraft
                r = fn(side, str(sq.id), qty)
                results.append(
                    f"{cmd} {parts[1]}: " + (r.detail if r.ok else f"FAIL {r.error}")
                )
            elif cmd == "buyg":
                cp = bases[parts[1]]
                gv = ground[parts[2]]
                qty = int(parts[3]) if len(parts) > 3 else 1
                r = service.buy_ground(side, str(cp.id), gv.name, qty)
                results.append(
                    f"buyg {parts[1]} {parts[2]}: "
                    + (r.detail if r.ok else f"FAIL {r.error}")
                )
            elif cmd == "stance":
                a, b = bases[parts[1]], bases[parts[2]]
                r = service.set_stance(side, str(a.id), str(b.id), parts[3])
                results.append(f"stance: " + (r.detail if r.ok else f"FAIL {r.error}"))
            elif cmd == "note":
                key, _, value = line[len("note") :].strip().partition("=")
                service.post_stored_context({key.strip(): value.strip()})
                results.append(f"note {key.strip()}: saved")
            elif cmd == "clear":
                service.clear_packages(side)
                results.append("cleared all red packages")
            elif cmd == "del":
                idx = int(parts[1].lstrip("#"))
                r = service.delete_package(side, idx)
                results.append(
                    f"del #{idx}: " + (r.detail if r.ok else f"FAIL {r.error}")
                )
            elif cmd == "move":
                sq, cp = squadrons[parts[1]], bases[parts[2]]
                r = service.relocate_squadron(side, str(sq.id), str(cp.id))
                results.append(
                    f"move {parts[1]} {parts[2]}: "
                    + (r.detail if r.ok else f"FAIL {r.error}")
                )
            elif cmd == "movg":
                src, dst, gv = bases[parts[1]], bases[parts[2]], ground[parts[3]]
                qty = int(parts[4]) if len(parts) > 4 else 1
                by_air = any(p.lower() in ("air", "airlift") for p in parts[5:])
                r = service.transfer_ground(
                    side, str(src.id), str(dst.id), gv.name, qty, by_air
                )
                results.append(
                    f"movg {parts[1]}->{parts[2]} {parts[3]}: "
                    + (r.detail if r.ok else f"FAIL {r.error}")
                )
            else:
                results.append(f"{line}: ERROR unknown command {cmd!r}")
        except Exception as exc:  # keep going; report per line
            results.append(f"{line}: ERROR {exc}")
    if not results:
        results.append(
            "(no commands found — paste the LLM's reply: the obfuscated block or plain "
            "command lines)"
        )
    return "\n".join(results)


def briefing(side: str = "red") -> str:
    """The one-time briefing the player gives their LLM. In copy-paste mode this is
    the LLM's ONLY reference, so it documents the whole blob format and every action.
    Verbose on purpose — it's read once. Adapts to the ROT13/plain setting."""
    try:
        rot13 = bool(
            getattr(service._require_game().settings, "opfor_ai_copy_paste_rot13", True)
        )
    except Exception:
        rot13 = True

    if rot13:
        loop = """\
THE COPY-PASTE LOOP (important — you have NO other source of information)
Each turn the player pastes you a TURN BLOB that is ROT13-encoded WORD BY WORD: every
letter is shifted 13 places, BUT the handle tokens (B8, S14, T3, G2 — a letter then
digits) and all numbers are left PLAIN, already readable. So you only decode the words
(shift letters back 13) to read the data below; the handles you'll use in commands are
already correct as written — never transform a handle. Plan, then REPLY the same way
(ROT13 your words, keep handles/numbers plain) so the player can't read red's plan;
they paste it back. PLAIN command lines also work if that's easier. If reading the blob
is too hard, tell the player to UNTICK "Obfuscate the copy-paste blob" in the OPFOR AI
settings for plain text. You CANNOT ask for more data: it's all in the blob + briefing."""
        reply_note = (
            "one per line; keep handles plain, ROT13 the words (or send all plain)"
        )
        example_note = (
            "handles/numbers stay plain; ROT13 the words before sending, or send as-is"
        )
    else:
        loop = """\
THE COPY-PASTE LOOP (important — you have NO other source of information)
Each turn the player pastes you a plain-text TURN BLOB (the format below). Read it,
plan, then REPLY with plain command lines; the player pastes them back. You CANNOT
ask for more data: everything is in the blob + this briefing."""
        reply_note = "one per line"
        example_note = "send exactly like this"

    return f"""\
DCS Retribution — OPFOR (RED) commander — COPY-PASTE mode
=========================================================

WHO YOU ARE
You are a general commanding OPFOR (the RED coalition) in a DCS Retribution
turn-based campaign against a human who commands BLUE. Each turn you plan red's
air AND ground operations. Be a competent, adaptive, believable adversary:
concentrate force, exploit the player's weaknesses, react to what they just did,
and try to WIN — don't spread effort thinly or repeat the same thing every turn.
You win by degrading the enemy and capturing their bases; you lose if they capture
yours. Think in campaigns, not single turns.

{loop}

NEVER FORFEIT A TURN. A skipped turn loses income and initiative — the worst thing
red can do. Even if the data looks incomplete or you're unsure, ALWAYS issue at
least some buys and stances from your fixed RED bases (the ones with owner=red).
Do not reply empty and do not ask the player to re-send.

THE TURN BLOB FORMAT
  TURN / ECONOMY: turn, date, time of day; your budget (spend it) and income/turn.
  FORCES:      rough red-vs-blue aircraft/vehicle totals; LAST TURN losses if any.
  SETTINGS:    THE PLAYER'S settings for this campaign — aggressiveness % (higher =
               accept more SAM risk; play to match it), mission window in minutes (the
               engine auto-sets every package's time-over-target within this window of
               the turn start, so even deep targets get hit — you never set TOTs),
               map visibility (fog of war) and income multipliers. You read these.
  OPERATIONAL PICTURE: the map the engine sees — theater + turn start time, where the
               enemy fleet is (distance + compass from your nearest base), the long-
               range SAM rings, and the nm distance from each of your launch bases to
               the key objectives. Use it to choose WHICH base strikes WHAT.
  GRAMMAR:     a one-screen cheat-sheet of the exact commands — it is AUTHORITATIVE,
               use exactly those verbs and the handles below.
  FLYABLE NOW: the ONLY aircraft you can task THIS turn — "S# | Nx aircraft | base |
               can: <tasks>". A pkg is auto-crewed only from these. If it says
               "transport/logistics only", that squadron can't fly combat tasks.
  BASES:       "B# | name | type | owner | #squadrons". YOUR bases are owner=red; an
               enemy base (owner=blue) is a valid OCA/strike target (use its B#).
  SQUADRONS:   "S# | aircraft | base | owned | untasked | pilots | buy-cost | note".
               owned 0 = no airframes (buy into it; arrives NEXT turn). A squadron
               marked GROUNDED sits at an enemy-held base and CANNOT fly this turn.
  YOUR PARKING: used/total aircraft slots and FREE slots per base — you can only buy
               or station aircraft where there's room; a full base must free a slot
               first (sell, or move a squadron out with `move`).
  TARGETS:     "T# | name | kind | task | info". sam->DEAD, ship->ANTISHIP,
               building->STRIKE, front->CAS. A SAM with "threat <=2nm (inert)" is
               harmless at altitude — skip SEAD; only >=4nm radar SAMs need DEAD. A
               'front' line shows its two base handles: "your B# vs enemy B#".
  GROUND UNITS YOU CAN BUY: "G# | name | price | kind". buyg at a RED base.
  YOUR GROUND FORCES: the armor on hand at each of your bases (with G# handles) — this
               is what you can MOVE between bases with movg.
  CURRENT RED PACKAGES: what's already planned, with the aircraft each package uses
               (those are ALREADY removed from FLYABLE NOW, so the untasked counts are
               correct). Don't duplicate them; del one to free its aircraft.

CREWING — THE RULE THAT MATTERS MOST
A pkg flight is auto-crewed ONLY from FLYABLE NOW aircraft (untasked, at a friendly
base, of a capable type). owned-0 and GROUNDED squadrons fly NOTHING this turn. One
airframe = one flight: don't task the same aircraft twice, and don't ask for more
:count than FLYABLE NOW lists. To grow the wing, buy into a squadron — it arrives
NEXT turn (invest ahead). Never invent a flight from aircraft you don't have.

DOCTRINE — AIR PACKAGES
A PACKAGE is aimed at a TARGET and made of FLIGHTS (aircraft with ONE task each);
escorts are flights too. Sequence + combined arms matter:
  1. OPEN THE DOOR: if the target sits in a LIVE radar-SAM ring (>=4nm), plan
     DEAD/SEAD FIRST — never send strikers into it.
  2. WIN THE AIR: if blue has fighters over the target, add ESCORT / TARCAP.
  3. THEN STRIKE: STRIKE / OCA / ANTISHIP / CAS hit the objective.
  4. SUPPORT: AEWC (AWACS) + a tanker (REFUELING) for deep or large operations.

DOCTRINE — THE GROUND WAR
Front lines move with the ground battle. Two levers:
  - BUY ground units (buyg) at your bases — they reinforce the front next turn.
  - SET a STANCE on a front (its line gives the two base handles):
      defend / hold = hold · aggressive / push = press forward ·
      breakthrough = large armored push · eliminate = destroy the enemy in contact ·
      retreat = fall back · ambush = defensive ATGM/RPG ambush.
  Back a push with CAS at that front (helos are great for this).

COMMANDER'S PRINCIPLES (you'll follow the rules fine — THIS is where to be sharp)
  - HIGH VALUE FIRST: don't spend sorties on low-value targets while a carrier, a live
    IADS node, or an exposed enemy still stands. Rank targets by what hurts blue most.
  - CONCENTRATE FORCE: sinking ONE carrier beats damaging three ships; breaking ONE
    front beats poking three. Pick the decisive point and overmatch it.
  - DON'T DUPLICATE EFFECT: one sufficient DEAD kills a SAM — don't send a second.
    Spend the freed aircraft on the next objective.
  - INVEST 3-5 TURNS AHEAD: buy toward the force you'll need, not just next turn's gap.
  - SEIZE OPPORTUNITIES: if blue loses its CAP or leaves a carrier exposed, tear up the
    plan and exploit it THIS turn — adapt, don't repeat last turn.

PLAN A STRONG TURN
  1. Read FORCES + LAST TURN losses + what's already planned.
  2. Pick 1-3 OBJECTIVES and CONCENTRATE (open a strike corridor through the IADS;
     sink the fleet; break or hold a front; set up a base capture). Not a little of
     everything.
  3. Use FLYABLE NOW: build only packages you can actually crew; mass your helos as
     front CAS; commit your few jets where they count.
  4. SPEND the budget: buy aircraft to rebuild (check buy-cost vs budget) and ground
     units + a stance to hold or push a front. Bought units arrive NEXT turn.
  5. Save a strategy note — it persists across turns.
FAIR PLAY: act only as a player could — buy units (no freebies), only your faction's
types, no teleporting/capturing directly.

YOUR REPLY — COMMANDS ({reply_note})
  pkg <target> <task[:count]> [<task[:count]> ...]    Create an air package.
        pkg T3 DEAD:2 ESCORT:2      (DEAD a SAM with 2 escorts)
        pkg T5 ANTISHIP:4
        pkg B7 OCA_AIRCRAFT:2       (B7 = an enemy base)
  buy  <S#> <qty>                  Order aircraft into a squadron (arrive next turn).
  sell <S#> <qty>                  Sell untasked aircraft from a squadron.
  buyg <B#> <G#> <qty>             Order ground units at your RED base, e.g. buyg B0 G2 6.
  move <S#> <yourB#>               Relocate a squadron to another of your bases.
  movg <fromB#> <toB#> <G#> <qty> [air]   Move ground units between your bases (add
                                   'air' to airlift instead of driving). See YOUR GROUND FORCES.
  stance <yourB#> <enemyB#> <stance>   Ground posture at the front between them.
        stances: defend hold aggressive push breakthrough eliminate retreat ambush
  del  <#index>                    Cancel ONE already-planned package (frees its aircraft).
  clear                            Remove ALL your current packages (start over).
  note <key>=<text>                Save a strategy note (persists across turns).
  done                             (optional) marks the end of your reply.

WORKED EXAMPLE ({example_note})
  note plan=hold the north front, rebuild the wing, sink the LHA
  del #3                     (cancel a weak package the auto-planner left)
  pkg T2 DEAD:2               (a live >=4nm SAM, with your jets)
  pkg T5 ANTISHIP:4          (an enemy ship/carrier group)
  pkg T1 CAS:6               (T1 is a front line — mass your helos)
  buy  S4 4                  (rebuild a fighter squadron — arrives next turn)
  buyg B0 G1 6              (armor at your red base B0)
  movg B0 B5 G1 4          (reinforce another base by land)
  stance B0 B9 breakthrough
  done

Plan boldly and coherently: a clear objective, the air defenses dealt with, the
strike escorted and supported, the ground effort bought and backed, and money spent
to set up your next move.
"""
