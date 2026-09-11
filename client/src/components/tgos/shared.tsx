import { Tgo as TgoModel } from "../../api/liberationApi";
import SplitLines from "../splitlines/SplitLines";
import { Icon, Point } from "leaflet";
import ms from "milsymbol";
import { Tooltip } from "react-leaflet";

// milsymbol 3.x paints the operational-condition health bar yellow for "damaged".
// Health-bar contract (server digit in game/theater/theatergroundobject.py):
// green = intact, yellow = damaged, red = all dead unrepaired — and ORANGE, done
// here by recolouring the yellow bar, whenever repairs are pending on the dead
// parts (partial or fully-dead alike, per the server's `repairing` flag).
const MILSYMBOL_DAMAGED_YELLOW = "rgb(255,255,0)";
const REPAIRING_ORANGE = "rgb(255,140,0)";

// APP-6(D) SIDC (see game/sidc.py): the status/condition digit is at index 6.
// "3" == Present/Damaged (the yellow bar). Only a damaged bar gets recoloured:
// a fully-dead unrepaired group carries "4" (red) and stays red.
export function isRepairing(tgo: TgoModel): boolean {
  return tgo.repairing === true && tgo.sidc.charAt(6) === "3";
}

// Entity field of the SIDC, characters 10-15. 150504 is electronic warfare /
// jamming, which milsymbol letters "EW" -- true but not the useful half: what these
// sites jam is GPS, and nothing else on the map does.
const JAMMING_ENTITY = "150504";

export function isJammer(tgo: TgoModel): boolean {
  return tgo.sidc.slice(10, 16) === JAMMING_ENTITY;
}

// milsymbol renders the letters as one <text> and picks the size from the string's
// length at icon-definition time, so a three-letter swap has to carry its own size
// or it overflows the frame.
function relabelAsGps(svg: string): string {
  return svg
    .replace(
      /(<text[^>]*?)font-size="45"([^>]*>)EW<\/text>/,
      '$1font-size="39"$2GPS</text>',
    )
    .replace(/>EW<\/text>/, ">GPS</text>");
}

export function iconForTgo(tgo: TgoModel) {
  const symbol = new ms.Symbol(tgo.sidc, { size: 24 });
  const iconAnchor = new Point(symbol.getAnchor().x, symbol.getAnchor().y);
  const repairing = isRepairing(tgo);
  const jammer = isJammer(tgo);
  if (!repairing && !jammer) {
    return new Icon({ iconUrl: symbol.toDataURL(), iconAnchor });
  }
  let svg = symbol.asSVG();
  if (repairing) {
    svg = svg.split(MILSYMBOL_DAMAGED_YELLOW).join(REPAIRING_ORANGE);
  }
  if (jammer) {
    svg = relabelAsGps(svg);
  }
  return new Icon({
    iconUrl: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg),
    iconAnchor,
  });
}

export function TgoTooltip(props: { tgo: TgoModel }) {
  return (
    <Tooltip>
      {`${props.tgo.name} (${props.tgo.control_point_name})`}
      <br />
      <SplitLines items={props.tgo.units} />
      <IadsStateLine tgo={props.tgo} />
    </Tooltip>
  );
}

// What the IADS will do with this site once the mission starts, and why. Only shown
// when it is something other than a site working as designed: saying "networked" on
// every SAM on the map would be noise.
export function IadsStateLine(props: { tgo: TgoModel }) {
  const label = iadsStateLabel(props.tgo);
  if (label == null) {
    return null;
  }
  return (
    <div style={{ marginTop: "0.4em", opacity: 0.85 }}>
      <b>{label}</b>
      {props.tgo.iads_reason ? <div>{props.tgo.iads_reason}</div> : null}
    </div>
  );
}

export function iadsStateLabel(tgo: TgoModel): string | null {
  if (tgo.iads_state === "dark") {
    return tgo.iads_blind ? "IADS: dark, and blind" : "IADS: dark";
  }
  if (tgo.iads_state === "autonomous") {
    return tgo.iads_blind ? "IADS: autonomous, and blind" : "IADS: autonomous";
  }
  if (tgo.iads_blind) {
    return "IADS: no radar of its own";
  }
  return null;
}
