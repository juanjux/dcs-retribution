"""Copy-paste transport for free-LLM accounts (no API / no MCP).

In copy-paste mode the LLM has ONLY the one-time briefing plus each turn's blob —
it cannot call any read/action endpoint — so the briefing is a COMPLETE,
self-contained reference (blob format + every action) and the blob carries
everything the LLM needs (incl. the settings and the buyable ground units).

The turn data is ROT13-obfuscated (opfor_ai_copy_paste_rot13, on by default) so the
player can't read red's state/plan at a glance — a capable LLM decodes ROT13 in its
head, unlike base64 which made every model forfeit the turn. Untick the setting for
plain text. The reply is accepted plain, ROT13, or (legacy) base64. Objects use short
handles (B# base, S# squadron, T# target, G# buyable ground unit), deterministic
within a turn.
"""

from __future__ import annotations

import base64
import codecs
import re

from game.ato.flighttype import FlightType
from game.agent import service, views

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


def _capable_tasks(sq) -> list[str]:
    out = []
    for ft in _ROLE_TASKS:
        try:
            if sq.capable_of(ft):
                out.append(ft.name)
        except Exception:
            pass
    return out


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

    out += [
        f"SETTINGS: aggressiveness {st.opfor_aggressiveness_pct}% (higher = take more "
        f"risk vs enemy SAMs) | mission window {st.desired_player_mission_duration_min} "
        f"min (aim every package's TOT within this) | map visibility "
        f"{st.map_coalition_visibility} | income multiplier you/enemy "
        f"{st.player_income_multiplier}/{st.enemy_income_multiplier}.",
        "",
        "GRAMMAR — reply with these commands, ONE PER LINE:",
        "  pkg <T#|enemyB#> <TASK[:count]> [<TASK[:count]> ...]   buy <S#> <n>   "
        "sell <S#> <n>",
        "  buyg <yourB#> <G#> <n>   stance <yourB#> <enemyB#> <stance>   "
        "note <key>=<text>   clear",
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
            note = " | GROUNDED: base is enemy-held, can't fly"
        out.append(
            f"{h} | {sq.aircraft.display_name} | {bh} {sq.location.name} | "
            f"{sq.owned_aircraft} | {sq.untasked_aircraft} | "
            f"{sq.number_of_available_pilots} | buy {price}{note}"
        )
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
    out += [
        "",
        "CURRENT RED PACKAGES — already planned this turn (index | target | task | tot)",
    ]
    for p in pkgs:
        out.append(f"#{p.index} | {p.target} | {p.task} | {p.tot or '?'}")
    return "\n".join(out)


def outgoing_blob(side: str = "red") -> str:
    """The turn snapshot, ROT13-obfuscated when enabled (a capable LLM decodes it in
    its head) or plain when not — base64 is gone: hand-decoding it made LLMs forfeit."""
    plain = _plain_outgoing(side)
    game = service._require_game()
    if getattr(game.settings, "opfor_ai_copy_paste_rot13", True):
        return _rot13(plain)
    return plain


def _maybe_decode(text: str) -> str:
    """Accept the reply as plain, ROT13, or (legacy) base64 — pick whichever yields
    our command grammar, else treat it as plain."""
    if _looks_like_commands(text):
        return text
    rotated = _rot13(text)
    if _looks_like_commands(rotated):
        return rotated
    candidate = "".join(text.split())  # base64 ignores whitespace; commands don't
    try:
        decoded = base64.b64decode(candidate, validate=True).decode("utf-8")
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
Each turn the player pastes you a TURN BLOB that is ROT13-encoded (every LETTER is
shifted 13 places; digits, '|' and numbers are unchanged, so handles like B8, T3,
S14, G2 keep their digits). Decode it in your head to read the data described below.
Plan, then REPLY in ROT13 too (shift your letters 13 places) so the player can't read
red's plan; they paste it back. If you can't ROT13 reliably, reply in PLAIN command
lines — it still works. If even reading the blob is too hard, tell the player to
UNTICK "Obfuscate the copy-paste blob with ROT13" in the OPFOR AI settings to switch
to plain text. You CANNOT ask for more data: everything is in the blob + this briefing."""
        reply_note = "one per line; then ROT13-encode the whole reply (or send plain)"
        example_note = "plain — ROT13-encode it before sending, or send as-is"
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
  SETTINGS:    aggressiveness % (higher = accept more SAM risk), mission window in
               minutes (aim EVERY package's TOT within it), map visibility, income
               multipliers. You read these; you never change them.
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
  TARGETS:     "T# | name | kind | task | info". sam->DEAD, ship->ANTISHIP,
               building->STRIKE, front->CAS. A SAM with "threat <=2nm (inert)" is
               harmless at altitude — skip SEAD; only >=4nm radar SAMs need DEAD. A
               'front' line shows its two base handles: "your B# vs enemy B#".
  GROUND UNITS YOU CAN BUY: "G# | name | price | kind". buyg at a RED base.
  CURRENT RED PACKAGES: already planned this turn (don't duplicate it).

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
  stance <yourB#> <enemyB#> <stance>   Ground posture at the front between them.
        stances: defend hold aggressive push breakthrough eliminate retreat ambush
  note <key>=<text>                Save a strategy note (persists across turns).
  clear                            Remove all your current packages (start over).
  done                             (optional) marks the end of your reply.

WORKED EXAMPLE ({example_note})
  note plan=hold the north front, rebuild the wing, sink the LHA
  pkg T2 DEAD:2               (a live >=4nm SAM, with your jets)
  pkg T5 ANTISHIP:4          (an enemy ship/carrier group)
  pkg T1 CAS:6               (T1 is a front line — mass your helos)
  buy  S4 4                  (rebuild a fighter squadron — arrives next turn)
  buyg B0 G1 6              (armor at your red base B0)
  stance B0 B9 breakthrough
  done

Plan boldly and coherently: a clear objective, the air defenses dealt with, the
strike escorted and supported, the ground effort bought and backed, and money spent
to set up your next move.
"""
