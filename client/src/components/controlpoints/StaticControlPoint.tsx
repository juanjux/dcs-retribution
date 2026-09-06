import { ControlPoint } from "../../api/_liberationApi";
import {
  selectHighlightEmitters,
  selectHoveredEmitter,
  setHoveredEmitter,
} from "../../api/mapSlice";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { makeLocationMarkerEventHandlers } from "./EventHandlers";
import { iconForControlPoint } from "./Icons";
import LocationTooltipText from "./LocationTooltipText";
import { Marker, Tooltip } from "react-leaflet";

interface StaticControlPointProps {
  controlPoint: ControlPoint;
}

export const StaticControlPoint = (props: StaticControlPointProps) => {
  const dispatch = useAppDispatch();
  // Raised above other icons while this emitter (or its ring) is hovered.
  const raised = useAppSelector(
    (state) =>
      selectHighlightEmitters(state) &&
      selectHoveredEmitter(state) === props.controlPoint.id
  );
  return (
    <Marker
      position={props.controlPoint.position}
      icon={iconForControlPoint(props.controlPoint)}
      // We might draw other markers on top of the CP. The tooltips from the
      // other markers are helpful so we want to keep them, but make sure the CP
      // is always the clickable thing.
      zIndexOffset={raised ? 10000 : 1000}
      eventHandlers={{
        ...makeLocationMarkerEventHandlers(props.controlPoint),
        // Hovering the carrier highlights its escorts' rings (and vice versa).
        mouseover: () =>
          dispatch(
            setHoveredEmitter({ id: props.controlPoint.id, source: "emitter" })
          ),
        mouseout: () => dispatch(setHoveredEmitter(null)),
      }}
    >
      <Tooltip>
        <LocationTooltipText
          name={props.controlPoint.name}
          units={props.controlPoint.units}
          tacan={props.controlPoint.tacan}
          atcFrequency={props.controlPoint.atc_frequency}
        />
      </Tooltip>
    </Marker>
  );
};
