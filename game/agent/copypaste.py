"""Copy-paste transport for free-LLM accounts (no API / no MCP).

The player copies the *outgoing* turn blob to their LLM and pastes the LLM's
*response* blob back. Both are compact TEXT — NOT zlib/base64 — because the LLM
reads them directly; compression would not cut token count. Token economy comes
from short handles (``B``/``S``/``T`` + index) instead of UUIDs and a terse
line-oriented command grammar. Handles are deterministic within a turn, so the
same enumeration resolves them on the way back in.
"""

from __future__ import annotations

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


def outgoing_blob(side: str = "red") -> str:
    """The compact turn snapshot for the LLM to read."""
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
        out.append(
            f"{h} | {t.name} | {t.kind} | {t.suggested_task}"
            + (f" | {t.threat_nm}nm" if t.threat_nm else "")
        )
    out += ["", "CURRENT RED PACKAGES (index | target | task | tot)"]
    for p in pkgs:
        out.append(f"#{p.index} | {p.target} | {p.task} | {p.tot or '?'}")
    out += ["", "Reply with commands (see the briefing). End with: done"]
    return "\n".join(out)


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

    for raw in text.splitlines():
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
        results.append("(no commands found)")
    return "\n".join(results)


def briefing(side: str = "red") -> str:
    """One-time briefing shown when copy-paste mode is enabled (verbose is fine)."""
    return (
        "DCS Retribution — OPFOR AI, COPY-PASTE mode\n"
        "===========================================\n\n"
        "You are the RED (OPFOR) commander. Each turn the player pastes you a TURN "
        "BLOB (situation, your bases/squadrons, enemy TARGETS, your current packages). "
        "You reply with COMMANDS; the player pastes them back into the game.\n\n"
        "Objects are referenced by short handles from the blob: B# = base, S# = "
        "squadron, T# = enemy target. (B# can also be a strike/OCA target.)\n\n"
        "COMMANDS (one per line):\n"
        "  pkg <target> <task[:count]> [<task[:count]> ...]\n"
        "        Create a package at a target with one or more flights.\n"
        "        Tasks: DEAD SEAD BARCAP TARCAP ESCORT OCA_AIRCRAFT OCA_RUNWAY\n"
        "               STRIKE ANTISHIP CAS BAI AEWC REFUELING EWAR\n"
        "        e.g.  pkg T3 DEAD:2 ESCORT:2     (DEAD a SAM, with 2 escorts)\n"
        "              pkg T5 ANTISHIP:4          (4-ship anti-ship strike)\n"
        "  buy <squadron> <qty>      Order aircraft (arrive next turn).\n"
        "  sell <squadron> <qty>     Sell untasked aircraft.\n"
        "  stance <baseA> <baseB> <stance>   Ground posture between two bases.\n"
        "        stances: defend hold aggressive push breakthrough eliminate retreat ambush\n"
        "  note <key>=<text>         Save a strategy note (persists across turns).\n"
        "  clear                     Remove all your current packages.\n"
        "  done                      (optional) end of your reply.\n\n"
        "Plan boldly: open SAM rings with DEAD first, escort strikers, time TOTs "
        "within the mission window, and spend to fix gaps. Keep every flight crewed "
        "(the game auto-assigns pilots). Concentrate force on 1-3 objectives.\n"
    )
