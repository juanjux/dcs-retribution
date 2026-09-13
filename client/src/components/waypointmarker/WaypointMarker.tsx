import {
  Flight,
  Waypoint,
  useSetWaypointPositionMutation,
} from "../../api/liberationApi";
import "./WaypointMarker.css";
import { Icon } from "leaflet";
import { Marker as LMarker } from "leaflet";
import icon from "leaflet/dist/images/marker-icon.png";
import iconShadow from "leaflet/dist/images/marker-shadow.png";
import { MutableRefObject, useCallback, useEffect, useRef } from "react";
import { Marker, Tooltip, useMap, useMapEvent } from "react-leaflet";

const WAYPOINT_ICON = new Icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconAnchor: [12, 41],
});

// The same pin, lit up. A class rather than a second image: one icon to keep.
const SELECTED_ICON = new Icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconAnchor: [12, 41],
  className: "wp-marker-selected",
});

// The target, in red. The route no longer runs through it, so this mark is the only
// thing that says where the flight is going -- and a strike with several aim points
// gets one each, which the single line through them never showed.
const TARGET_ICON = new Icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconAnchor: [12, 41],
  className: "wp-marker-target",
});

const SELECTED_TARGET_ICON = new Icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconAnchor: [12, 41],
  className: "wp-marker-target wp-marker-selected",
});

/** Which of the four pins this waypoint gets. */
function iconFor(isTarget: boolean, selected: boolean): Icon {
  if (isTarget) {
    return selected ? SELECTED_TARGET_ICON : TARGET_ICON;
  }
  return selected ? SELECTED_ICON : WAYPOINT_ICON;
}

interface WaypointMarkerProps {
  number: number;
  waypoint: Waypoint;
  flight: Flight;
  selected: boolean;
  onSelect: () => void;
  onOpen: (at: { x: number; y: number }) => void;
  onMenu: (at: { x: number; y: number }) => void;
}

const WaypointMarker = (props: WaypointMarkerProps) => {
  // Most props of react-leaflet types are immutable and components will not
  // update to account for changes, so we can't simply use the `permanent`
  // property of the tooltip to control tooltip visibility based on the zoom
  // level.
  //
  // On top of that, listening for zoom changes and opening/closing is not
  // sufficient because clicking anywhere will close any opened tooltips (even
  // if they are permanent; once openTooltip has been called that seems to no
  // longer have any effect).
  //
  // Instead, listen for zoom changes and rebind the tooltip when the zoom level
  // changes.
  const map = useMap();
  const marker: MutableRefObject<LMarker | undefined> = useRef();

  const [putDestination] = useSetWaypointPositionMutation();

  const rebindTooltip = useCallback(() => {
    if (marker.current === undefined) {
      return;
    }

    const tooltip = marker.current.getTooltip();
    if (tooltip === undefined) {
      return;
    }

    const permanent = map.getZoom() >= 9;
    marker.current
      .unbindTooltip()
      .bindTooltip(tooltip, { permanent: permanent });
  }, [map]);
  useMapEvent("zoomend", rebindTooltip);

  useEffect(() => {
    const waypoint = props.waypoint;
    marker.current?.setTooltipContent(
      `${props.number - 1} ${waypoint.name}<br />` +
        `${waypoint.altitude_ft.toFixed()} ft ${waypoint.altitude_reference}<br />` +
        waypoint.timing,
    );
  });

  const waypoint = props.waypoint;
  return (
    <Marker
      position={waypoint.position}
      icon={iconFor(waypoint.is_target, props.selected)}
      draggable
      eventHandlers={{
        click: () => props.onSelect(),
        dblclick: (e) => {
          // Leaflet's own double-click zooms the map. Editing a waypoint is not a
          // reason to change what you are looking at.
          e.originalEvent.preventDefault();
          e.originalEvent.stopPropagation();
          props.onSelect();
          props.onOpen({
            x: e.originalEvent.clientX,
            y: e.originalEvent.clientY,
          });
        },
        contextmenu: (e) => {
          e.originalEvent.preventDefault();
          props.onSelect();
          props.onMenu({
            x: e.originalEvent.clientX,
            y: e.originalEvent.clientY,
          });
        },
        dragstart: (e) => {
          const m: LMarker = e.target;
          m.setTooltipContent("Waiting to recompute TOT...");
        },
        dragend: async (e) => {
          const m: LMarker = e.target;
          const destination = m.getLatLng();
          try {
            await putDestination({
              flightId: props.flight.id,
              waypointIdx: props.number,
              leafletPoint: { lat: destination.lat, lng: destination.lng },
            });
          } catch (e) {
            console.error("Failed to set waypoint position", e);
          }
        },
      }}
      ref={(ref) => {
        if (ref != null) {
          marker.current = ref;
        }
      }}
    >
      <Tooltip position={waypoint.position} />
    </Marker>
  );
};

export default WaypointMarker;
