import { IadsConnection as IadsConnectionModel } from "../../api/liberationApi";
import { Polyline as LPolyline } from "leaflet";
import { useRef } from "react";
import { Polyline, Tooltip } from "react-leaflet";

// Colour each IADS link by both kind and state, with tones picked to stay
// distinct from the other map layers:
//   Communication: green = active, red  = inactive
//   Power:         cyan  = active, gold = inactive
// Power's cyan avoids the routes / threat-zone blue (#0084ff), and its gold
// avoids the SAM detection-range yellow (#eee17b) and the highlight (#ffff00).
const COMMS_ACTIVE = "#2ecc40";
const COMMS_INACTIVE = "#ff4136";
const POWER_ACTIVE = "#00bcd4";
const POWER_INACTIVE = "#f1c40f";

interface IadsConnectionProps {
  iads_connection: IadsConnectionModel;
}

function linkColor(isPower: boolean, active: boolean): string {
  if (isPower) {
    return active ? POWER_ACTIVE : POWER_INACTIVE;
  }
  return active ? COMMS_ACTIVE : COMMS_INACTIVE;
}

function IadsConnectionTooltip(props: IadsConnectionProps) {
  const status = props.iads_connection.active ? "Active" : "Inactive";
  if (props.iads_connection.is_power) {
    return <Tooltip sticky>Power Connection ({status})</Tooltip>;
  } else {
    return <Tooltip sticky>Communication Connection ({status})</Tooltip>;
  }
}

export default function IadsConnection(props: IadsConnectionProps) {
  const { active, is_power } = props.iads_connection;
  const color = linkColor(is_power, active);
  const path = useRef<LPolyline | null>();
  const opacity = active ? 1.0 : 0.8;
  const dashArray = active ? "" : "20";

  return (
    <>
      {/* Visible, state- and kind-coloured line. */}
      <Polyline
        positions={props.iads_connection.points}
        color={color}
        weight={2}
        opacity={opacity}
        dashArray={dashArray}
        interactive={false}
        ref={(ref) => (path.current = ref)}
      />
      {/* Invisible, much wider line carrying the tooltip, so hovering has a
          comfortable margin instead of needing a pixel-perfect hit on the thin
          line. Leaflet interactive paths use pointer-events: auto, so a zero-
          opacity line still captures the mouse. */}
      <Polyline
        positions={props.iads_connection.points}
        weight={16}
        opacity={0}
      >
        <IadsConnectionTooltip {...props} />
      </Polyline>
    </>
  );
}
