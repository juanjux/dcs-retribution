"""Copy-paste transport for free-LLM accounts (no API / no MCP).

The player copies the *outgoing* turn blob to their LLM and pastes the LLM's
*response* blob back. The turn data is **base64-encoded** so the player can't read
red's full state / plan at a glance (it's obfuscation/friction, not encryption —
a determined player can still decode it; an LLM is told to decode it in the
briefing). The reply is accepted either base64-encoded (preferred — hides red's
plan from the player) or plain (still works). Token economy comes from short
handles (``B``/``S``/``T`` + index) instead of UUIDs and a terse command grammar.
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
    return bases, squadrons, targets


def _plain_outgoing(side: str) -> str:
    """The readable compact turn snapshot (before base64-encoding)."""
    game = service._require_game()
    tc = views.build_turn_context(game, side)
    pkgs = views.build_packages(game, side)
    sett = views.build_settings(game)
    bases, squadrons, targets = _build_handles(game, side)

    s, e = tc.situation, tc.economy
    out = [
        f"OPFOR TURN {s.turn} — you command RED. {s.date} {s.time_of_day}."
        + (f" [{s.campaign_state}]" if s.campaign_state else ""),
        f"budget {e.budget} | income/turn {e.income_next_turn} | aggressiveness "
        f"{sett.opfor_aggressiveness_pct}% | mission window {sett.desired_player_mission_duration_min}m",
        "",
        "BASES (handle | name | type | owner | squadrons)",
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
    out += ["", "TARGETS (handle | name | kind | suggested_task | threat)"]
    for h, t in targets.items():
        extra = ""
        if t.threat_nm:
            extra += f" | {t.threat_nm}nm"
        if t.kind == "front":
            extra += " | (front: use the two bases for stance/CAS)"
        out.append(f"{h} | {t.name} | {t.kind} | {t.suggested_task}{extra}")
    out += ["", "CURRENT RED PACKAGES (index | target | task | tot)"]
    for p in pkgs:
        out.append(f"#{p.index} | {p.target} | {p.task} | {p.tot or '?'}")
    return "\n".join(out)


def outgoing_blob(side: str = "red") -> str:
    """Base64 of the turn snapshot (so the player can't read it; the LLM decodes it)."""
    return base64.b64encode(_plain_outgoing(side).encode("utf-8")).decode("ascii")


def _maybe_decode(text: str) -> str:
    """Accept the reply as base64 (preferred) or plain. Decode only if the result
    actually looks like our command grammar, otherwise treat the text as plain."""
    candidate = "".join(text.split())  # base64 ignores whitespace; commands don't
    try:
        decoded = base64.b64decode(candidate, validate=True).decode("utf-8")
    except Exception:
        return text
    if re.search(r"(?im)^\s*(pkg|buy|sell|stance|note|clear)\b", decoded):
        return decoded
    return text


def apply_incoming(side: str, text: str) -> str:
    """Parse + execute the LLM's response commands; return a result blob."""
    game = service._require_game()
    bases, squadrons, targets = _build_handles(game, side)
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
            "(no commands found — did you paste the LLM's reply? it can be the "
            "base64 block or plain command lines)"
        )
    return "\n".join(results)


def briefing(side: str = "red") -> str:
    """The one-time briefing the player gives their LLM. Comprehensive on purpose —
    the LLM must play a whole campaign from this alone (verbose is fine, read once)."""
    return """\
DCS Retribution — OPFOR (RED) commander — COPY-PASTE mode
=========================================================

WHO YOU ARE
You are a general commanding OPFOR (the RED coalition) in a DCS Retribution
turn-based campaign, against a human who commands BLUE. Each turn you plan red's
air and ground operations. Be a competent, adaptive, believable adversary:
concentrate force, exploit the player's weaknesses, react to what they just did,
and try to WIN the campaign — do not spread effort thinly or do the same
predictable thing every turn. You win by degrading the enemy and capturing their
bases; you lose if they capture yours. Think in campaigns, not single turns.

HOW THE COPY-PASTE LOOP WORKS
Each turn the player pastes you a TURN BLOB that is BASE64-encoded. First DECODE
the base64 to get the readable turn data below. Plan the turn, then REPLY with
commands and BASE64-ENCODE your whole reply (so the player can't read red's plan).
The player pastes your reply back into the game.
  - If you cannot produce reliable base64, reply in PLAIN command lines instead —
    it still works; the player will just be able to read your commands.

THE TURN DATA (after you decode it)
  TURN line: turn #, date, your budget + income/turn, an aggressiveness hint
             (0-100; higher = take more risk), and the mission window in minutes.
  BASES:      B# | name | type | owner | #squadrons.  (An enemy base can be a target.)
  SQUADRONS:  S# | name | aircraft | base | owned | untasked | pilots.  (Your air wing.)
  TARGETS:    T# | name | kind | suggested_task | threat. Enemy objects you can hit:
              sam -> DEAD, ship -> ANTISHIP, building -> STRIKE, front -> CAS.
  CURRENT RED PACKAGES: what's already planned this turn (don't duplicate).

DOCTRINE — HOW TO BUILD PACKAGES
A mission is a PACKAGE aimed at a TARGET, made of FLIGHTS (a group of aircraft from
one squadron with ONE task). Escorts are flights too. Sequence + combined arms matter:
  1. OPEN THE DOOR: if the target sits inside radar-SAM range, plan DEAD/SEAD FIRST.
     Do NOT send strikers into a live SAM ring — they get turned back or shot down.
  2. WIN THE AIR: if blue has fighters over the target, add ESCORT / TARCAP.
  3. THEN STRIKE: STRIKE / OCA / ANTISHIP / CAS hit the actual objective.
  4. SUPPORT: add AEWC (AWACS) and a tanker (REFUELING) for deep or large operations.
Tasks: BARCAP TARCAP CAP SWEEP ESCORT SEAD DEAD STRIKE OCA_RUNWAY OCA_AIRCRAFT
       CAS BAI ANTISHIP AEWC REFUELING EWAR. Routes and pilots are automatic.

PLAN A STRONG TURN
  1. Read the situation and the previous result (your losses + what blue did).
  2. Pick 1-3 OBJECTIVES and CONCENTRATE on them (hold a threatened base; dismantle a
     section of blue's IADS to open a strike corridor; sink the fleet; break a front;
     set up a base capture). Do NOT plan a little of everything.
  3. Build properly-composed packages (above). Aim TOTs within the mission window.
  4. SPEND to fix gaps: buy fighters if you're losing the air war; buy/move ground
     units to hold or push a front. Bought aircraft arrive NEXT turn — invest ahead.
  5. Save a strategy note — it persists across turns so you can adapt.

FAIR PLAY: act only as a player could — no free aircraft (buy them), only airframes
your faction has, no teleporting or capturing bases directly. Every flight is crewed
automatically.

YOUR REPLY — COMMANDS (one per line; then base64-encode the whole reply)
  pkg <target> <task[:count]> [<task[:count]> ...]
        pkg T3 DEAD:2 ESCORT:2      (DEAD a SAM, with 2 escorts)
        pkg T5 ANTISHIP:4
        pkg B7 OCA_AIRCRAFT:2       (B7 = an enemy base; crater its parked aircraft)
  buy <squadron> <qty>             Order aircraft (arrive next turn).
  sell <squadron> <qty>            Sell untasked aircraft.
  stance <baseA> <baseB> <stance>  Ground posture at the front between two bases.
        stances: defend hold aggressive push breakthrough eliminate retreat ambush
  note <key>=<text>                Save a strategy note (persists across turns).
  clear                            Remove all your current packages (start over).
  done                             (optional) marks the end of your reply.

WORKED EXAMPLE (plain, before you base64-encode it)
  note plan=kill the north SAM belt this turn, strike the depot next turn
  pkg T2 DEAD:2 ESCORT:2
  pkg T7 STRIKE:2 SEAD:2
  buy S4 4
  stance B0 B9 breakthrough
  done

Plan boldly and coherently: a clear objective, the air defenses dealt with, the
strike escorted and supported, the ground effort backed up, and money spent to set
up your next move.
"""
