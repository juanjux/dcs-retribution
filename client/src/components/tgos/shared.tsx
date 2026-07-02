import { Tgo as TgoModel } from "../../api/liberationApi";
import SplitLines from "../splitlines/SplitLines";
import { Icon, Point } from "leaflet";
import ms from "milsymbol";
import { Tooltip } from "react-leaflet";

// milsymbol 3.x paints the operational-condition health bar yellow for "damaged".
// A fully-destroyed-but-repairing group carries that same yellow bar as a
// partially-damaged one, which is ambiguous — recolour it orange so "everything
// dead, repairing" reads distinctly from "some units dead, some alive".
const MILSYMBOL_DAMAGED_YELLOW = "rgb(255,255,0)";
const REPAIRING_ORANGE = "rgb(255,140,0)";

// APP-6(D) SIDC (see game/sidc.py): the status/condition digit is at index 6.
// "3" == Present/Damaged (the yellow bar). `dead` is only true when the WHOLE
// group is destroyed (partial damage keeps dead=false), so a dead group whose
// bar is still "damaged" is one being repaired — exactly the orange case.
export function isFullyDeadRepairing(tgo: TgoModel): boolean {
  return tgo.dead && tgo.sidc.charAt(6) === "3";
}

export function iconForTgo(tgo: TgoModel) {
  const symbol = new ms.Symbol(tgo.sidc, { size: 24 });
  const iconAnchor = new Point(symbol.getAnchor().x, symbol.getAnchor().y);
  if (isFullyDeadRepairing(tgo)) {
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
