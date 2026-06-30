"""Copy-paste transport for free-LLM accounts (no API / no MCP).

In copy-paste mode the LLM has ONLY the one-time briefing plus each turn's blob —
it cannot call any read/action endpoint — so the briefing is a COMPLETE,
self-contained reference (blob format + every action) and the blob carries
everything the LLM needs (incl. the settings and the buyable ground units).

The turn data is base64-encoded so the player can't read red's state/plan at a
glance (obfuscation/friction, not encryption). The reply is accepted base64
(preferred) or plain. Objects use short handles (B# base, S# squadron, T# target,
G# buyable ground unit), deterministic within a turn.
"""

from __future__ import annotations

import base64
import re

from game.agent import service, views


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


def _plain_outgoing(side: str) -> str:
    """The readable compact turn snapshot (before base64-encoding)."""
    game = service._require_game()
    tc = views.build_turn_context(game, side)
    pkgs = views.build_packages(game, side)
    st = views.build_settings(game)
    bases, squadrons, targets, ground = _build_handles(game, side)

    s, e = tc.situation, tc.economy
    out = [
        f"OPFOR TURN {s.turn} — you command RED. {s.date} {s.time_of_day}."
        + (f" [{s.campaign_state}]" if s.campaign_state else ""),
        f"ECONOMY: budget {e.budget}, income/turn {e.income_next_turn}.",
        f"SETTINGS: aggressiveness {st.opfor_aggressiveness_pct}% (higher = take more "
        f"risk vs enemy SAMs) | mission window {st.desired_player_mission_duration_min} "
        f"min (aim every package's TOT within this) | map visibility "
        f"{st.map_coalition_visibility} | income multiplier you/enemy "
        f"{st.player_income_multiplier}/{st.enemy_income_multiplier}.",
        "",
        "BASES (handle | name | type | owner | #squadrons)",
    ]
    for h, cp in bases.items():
        sqns = sum(1 for _ in cp.squadrons)
        out.append(
            f"{h} | {cp.name} | {cp.cptype.name} | {cp.captured.value.lower()} | {sqns}"
        )
    out += [
        "",
        "SQUADRONS (handle | name | aircraft | base | owned | untasked | pilots)",
    ]
    for h, sq in squadrons.items():
        out.append(
            f"{h} | {sq} | {sq.aircraft.display_name} | {sq.location.name} | "
            f"{sq.owned_aircraft} | {sq.untasked_aircraft} | {sq.number_of_available_pilots}"
        )
    out += [
        "",
        "TARGETS — enemy objects you can attack (handle | name | kind | task | threat)",
    ]
    for h, t in targets.items():
        extra = f" | threat {t.threat_nm}nm" if t.threat_nm else ""
        if t.kind == "front":
            extra += " | front: use its two bases for stance + CAS"
        out.append(f"{h} | {t.name} | {t.kind} | {t.suggested_task}{extra}")
    out += [
        "",
        "GROUND UNITS YOU CAN BUY (handle | name | price | kind) — buy at your bases",
    ]
    for h, gv in ground.items():
        out.append(f"{h} | {gv.name} | {gv.price} | {gv.kind}")
    out += [
        "",
        "CURRENT RED PACKAGES — already planned this turn (index | target | task | tot)",
    ]
    for p in pkgs:
        out.append(f"#{p.index} | {p.target} | {p.task} | {p.tot or '?'}")
    return "\n".join(out)


def outgoing_blob(side: str = "red") -> str:
    """Base64 of the turn snapshot (so the player can't read it; the LLM decodes it)."""
    return base64.b64encode(_plain_outgoing(side).encode("utf-8")).decode("ascii")


def _maybe_decode(text: str) -> str:
    """Accept the reply as base64 (preferred) or plain — decode only if the result
    actually looks like our command grammar, else treat the text as plain."""
    candidate = "".join(text.split())  # base64 ignores whitespace; commands don't
    try:
        decoded = base64.b64decode(candidate, validate=True).decode("utf-8")
    except Exception:
        return text
    if re.search(r"(?im)^\s*(pkg|buyg|buy|sell|stance|note|clear)\b", decoded):
        return decoded
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
            else:
                results.append(f"{line}: ERROR unknown command {cmd!r}")
        except Exception as exc:  # keep going; report per line
            results.append(f"{line}: ERROR {exc}")
    if not results:
        results.append(
            "(no commands found — paste the LLM's reply: the base64 block or plain "
            "command lines)"
        )
    return "\n".join(results)


def briefing(side: str = "red") -> str:
    """The one-time briefing the player gives their LLM. In copy-paste mode this is
    the LLM's ONLY reference, so it documents the whole blob format and every action.
    Verbose on purpose — it's read once."""
    return """\
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

THE COPY-PASTE LOOP (important — you have NO other source of information)
Each turn the player pastes you a TURN BLOB that is BASE64-encoded. DECODE the
base64 to get the readable turn data described below. Plan, then REPLY with command
lines and BASE64-ENCODE your whole reply (so the player can't read red's plan); the
player pastes it back. If you cannot produce reliable base64, reply in PLAIN command
lines instead — it still works, the player just sees your commands. You CANNOT ask
for more data: everything you get is in the blob + this briefing.

THE TURN BLOB FORMAT (after you base64-decode it)
  TURN line:   turn number, date, time of day, and campaign state.
  ECONOMY:     your budget (spend it this turn) and income per turn.
  SETTINGS:    aggressiveness % (higher = accept more SAM risk), the mission window
               in minutes (aim EVERY package's time-over-target within it — a TOT
               after the window is wasted), map visibility (fog level), and the
               income multipliers. You read these; you never change them.
  BASES:       one per line — "B# | name | type | owner | #squadrons". B# is a base
               handle. type is AIRBASE / *_CARRIER_GROUP / LHA_GROUP / FOB / FARP.
               An ENEMY base (owner=blue) is a valid OCA/strike target (use its B#).
  SQUADRONS:   "S# | name | aircraft | base | owned | untasked | pilots". Your air
               wing. S# is a squadron handle. 'untasked' = aircraft free to task
               THIS turn; 'owned' = total at the base; you buy into a squadron by S#.
  TARGETS:     enemy objects you can attack — "T# | name | kind | task | threat".
               kind/task: sam->DEAD, ship->ANTISHIP, building->STRIKE, front->CAS.
               'threat Xnm' is a SAM's reach. A 'front' line lists its two bases
               (use them for stance + CAS).
  GROUND UNITS YOU CAN BUY: "G# | name | price | kind" (front = tanks/IFVs,
               artillery). Buy them at one of YOUR bases to reinforce the ground war.
  CURRENT RED PACKAGES: what's already planned this turn (don't duplicate it).

DOCTRINE — AIR PACKAGES
A mission is a PACKAGE aimed at a TARGET, made of FLIGHTS (a group of aircraft from
one squadron with ONE task). Escorts are flights too. Sequence + combined arms matter:
  1. OPEN THE DOOR: if the target is inside radar-SAM range, plan DEAD/SEAD FIRST —
     never send strikers into a live SAM ring (they get turned back or shot down).
  2. WIN THE AIR: if blue has fighters over the target, add ESCORT / TARCAP.
  3. THEN STRIKE: STRIKE / OCA / ANTISHIP / CAS hit the objective.
  4. SUPPORT: AEWC (AWACS) + a tanker (REFUELING) for deep or large operations.
Tasks: BARCAP TARCAP CAP SWEEP ESCORT SEAD DEAD STRIKE OCA_RUNWAY OCA_AIRCRAFT
       CAS BAI ANTISHIP AEWC REFUELING EWAR. Routes and pilots are automatic.

DOCTRINE — THE GROUND WAR
Front lines move based on the ground battle. Two levers:
  - BUY ground units (buyg) at your bases — they reinforce the front next turn.
  - SET a STANCE on a front (between your base and the enemy base it faces):
      defend / hold = hold defensively · aggressive / push = press forward ·
      breakthrough = large armored push (very aggressive) ·
      eliminate = aggressively destroy the enemy in contact ·
      retreat = fall back · ambush = defensive ATGM/RPG ambush.
  Back a push with CAS at that front (a 'front' target).

PLAN A STRONG TURN
  1. Read the situation + the previous result (your losses, what blue did).
  2. Pick 1-3 OBJECTIVES and CONCENTRATE on them (hold a base; dismantle a section
     of blue's IADS to open a strike corridor; sink the fleet; break a front; set up
     a base capture). Do NOT plan a little of everything.
  3. Build properly-composed packages; aim TOTs within the mission window.
  4. SPEND to fix gaps: buy fighters if losing the air war; buy ground units + set a
     stance to hold or push a front. Bought units arrive NEXT turn — invest ahead.
  5. Save a strategy note — it persists across turns so you can adapt.
FAIR PLAY: act only as a player could — no free units (buy them), only your faction's
types, no teleporting/capturing directly. Flights are crewed automatically.

YOUR REPLY — COMMANDS (one per line; then base64-encode the whole reply)
  pkg <target> <task[:count]> [<task[:count]> ...]    Create an air package.
        pkg T3 DEAD:2 ESCORT:2      (DEAD a SAM with 2 escorts)
        pkg T5 ANTISHIP:4
        pkg B7 OCA_AIRCRAFT:2       (B7 = an enemy base)
  buy  <squadron> <qty>            Order aircraft into a squadron (arrive next turn).
  sell <squadron> <qty>            Sell untasked aircraft from a squadron.
  buyg <base> <ground-unit> <qty>  Order ground units at your base, e.g. buyg B0 G2 6.
  stance <yourBase> <enemyBase> <stance>   Ground posture at the front between them.
        stances: defend hold aggressive push breakthrough eliminate retreat ambush
  note <key>=<text>                Save a strategy note (persists across turns).
  clear                            Remove all your current packages (start over).
  done                             (optional) marks the end of your reply.

WORKED EXAMPLE (plain — base64-encode it before sending)
  note plan=kill the north SAM belt, then push the western front
  pkg T2 DEAD:2 ESCORT:2
  pkg T7 STRIKE:2 SEAD:2
  pkg T1 CAS:2                 (T1 is a front line)
  buy  S4 4
  buyg B0 G1 6
  stance B0 B9 breakthrough
  done

Plan boldly and coherently: a clear objective, the air defenses dealt with, the
strike escorted and supported, the ground effort bought and backed, and money spent
to set up your next move.
"""
