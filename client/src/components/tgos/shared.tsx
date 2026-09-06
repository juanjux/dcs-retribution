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

export function iconForTgo(tgo: TgoModel) {
  const symbol = new ms.Symbol(tgo.sidc, { size: 24 });
  const iconAnchor = new Point(symbol.getAnchor().x, symbol.getAnchor().y);
  if (isRepairing(tgo)) {
    const svg = symbol
      .asSVG()
      .split(MILSYMBOL_DAMAGED_YELLOW)
      .join(REPAIRING_ORANGE);
    return new Icon({
      iconUrl: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg),
      iconAnchor,
    });
  }
  return new Icon({ iconUrl: symbol.toDataURL(), iconAnchor });
}

export function TgoTooltip(props: { tgo: TgoModel }) {
  return (
    <Tooltip>
      {`${props.tgo.name} (${props.tgo.control_point_name})`}
      <br />
      <SplitLines items={props.tgo.units} />
    </Tooltip>
  );
}
