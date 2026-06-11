import {
  useOpenNewTgoPackageDialogMutation,
  useOpenTgoInfoDialogMutation,
} from "../../api/liberationApi";
import { Tgo as TgoModel } from "../../api/liberationApi";
import {
  selectHighlightEmitters,
  selectHoveredEmitter,
  setHoveredEmitter,
} from "../../api/mapSlice";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import SplitLines from "../splitlines/SplitLines";
import { Icon, Point } from "leaflet";
import ms from "milsymbol";
import { Marker, Tooltip } from "react-leaflet";

function iconForTgo(cp: TgoModel) {
  const symbol = new ms.Symbol(cp.sidc, {
    size: 24,
  });

  return new Icon({
    iconUrl: symbol.toDataURL(),
    iconAnchor: new Point(symbol.getAnchor().x, symbol.getAnchor().y),
  });
}

interface TgoProps {
  tgo: TgoModel;
}

export default function Tgo(props: TgoProps) {
  const [openNewPackageDialog] = useOpenNewTgoPackageDialogMutation();
  const [openInfoDialog] = useOpenTgoInfoDialogMutation();
  const dispatch = useAppDispatch();
  // Raised above other icons while this emitter (or its ring) is hovered.
  const raised = useAppSelector(
    (state) =>
      selectHighlightEmitters(state) &&
      selectHoveredEmitter(state) === props.tgo.id
  );
  return (
    <Marker
      position={props.tgo.position}
      icon={iconForTgo(props.tgo)}
      zIndexOffset={raised ? 10000 : 0}
      eventHandlers={{
        click: () => {
          openInfoDialog({ tgoId: props.tgo.id });
        },
        contextmenu: () => {
          openNewPackageDialog({ tgoId: props.tgo.id });
        },
        // Hovering the emitter highlights its ring (and vice versa).
        mouseover: () =>
          dispatch(setHoveredEmitter({ id: props.tgo.id, source: "emitter" })),
        mouseout: () => dispatch(setHoveredEmitter(null)),
      }}
    >
      <Tooltip>
        {`${props.tgo.name} (${props.tgo.control_point_name})`}
        <br />
        <SplitLines items={props.tgo.units} />
      </Tooltip>
    </Marker>
  );
}
