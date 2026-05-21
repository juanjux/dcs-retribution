import { selectControlPoints } from "../../api/controlPointsSlice";
import { selectTgos } from "../../api/tgosSlice";
import { setHoveredEmitter } from "../../api/mapSlice";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { LatLng } from "../../api/liberationApi";
import { Fragment, useState } from "react";
import { Circle, CircleMarker, LayerGroup } from "react-leaflet";

interface RangeCirclesProps {
  emitterId: string;
  position: LatLng;
  threat_ranges: number[];
  detection_ranges: number[];
  blue: boolean;
  detection?: boolean;
}

export function colorFor(blue: boolean, detection: boolean) {
  if (blue) {
    return detection ? "#bb89ff" : "#0084ff";
  }
  return detection ? "#eee17b" : "#c85050";
}

// Bright colour used to mark the hovered ring and its emitter.
const HIGHLIGHT_COLOR = "#ffff00";

const RangeCircles = (props: RangeCirclesProps) => {
  const radii = props.detection
    ? props.detection_ranges
    : props.threat_ranges;
  const color = colorFor(props.blue, props.detection === true);
  const baseWeight = props.detection ? 1 : 2;
  const [hovered, setHovered] = useState(false);
  const dispatch = useAppDispatch();

  const hover = {
    mouseover: () => {
      setHovered(true);
      dispatch(setHoveredEmitter(props.emitterId));
    },
    mouseout: () => {
      setHovered(false);
      dispatch(setHoveredEmitter(null));
    },
  };

  return (
    <>
      {radii.map((radius, idx) => (
        <Fragment key={idx}>
          <Circle
            center={props.position}
            radius={radius}
            color={hovered ? HIGHLIGHT_COLOR : color}
            fill={false}
            weight={hovered ? baseWeight + 2 : baseWeight}
            interactive={false}
          />
          {/* Invisible wide ring that catches the hover. The visible stroke is
              a fixed pixel width so it gets hard to hit when zoomed out; this
              18px transparent band (pointer-events: stroke via the className,
              so it works despite being invisible) gives a comfortable target
              along the perimeter without filling the disc. */}
          <Circle
            center={props.position}
            radius={radius}
            color={color}
            fill={false}
            opacity={0}
            weight={18}
            className="air-defense-ring-hit"
            eventHandlers={hover}
          />
        </Fragment>
      ))}
      {hovered && (
        <CircleMarker
          center={props.position}
          radius={20}
          color={HIGHLIGHT_COLOR}
          fillColor={HIGHLIGHT_COLOR}
          fillOpacity={0.5}
          weight={4}
          interactive={false}
          // Draw above the marker icons (markerPane, z 600) so the highlight is
          // not buried under a cluster of overlapping unit icons.
          pane="tooltipPane"
        />
      )}
    </>
  );
};

interface AirDefenseRangeLayerProps {
  blue: boolean;
  detection?: boolean;
}

export const AirDefenseRangeLayer = (props: AirDefenseRangeLayerProps) => {
  const tgos = Object.values(useAppSelector(selectTgos).tgos).filter(
    (tgo) => tgo.blue === props.blue
  );
  // Carrier/LHA control points carry their air-defense ranges (from the
  // surviving escort ships) directly, since their ship group is not emitted as
  // a standalone TGO. Draw their rings here too so a battered carrier group
  // does not look defenceless on the map.
  const controlPoints = Object.values(
    useAppSelector(selectControlPoints).controlPoints
  ).filter((cp) => cp.blue === props.blue);

  return (
    <LayerGroup>
      {tgos.map((tgo) => {
        return (
          <RangeCircles
            key={tgo.id}
            emitterId={tgo.id}
            position={tgo.position}
            threat_ranges={tgo.threat_ranges}
            detection_ranges={tgo.detection_ranges}
            {...props}
          />
        );
      })}
      {controlPoints.map((cp) => {
        return (
          <RangeCircles
            key={cp.id}
            emitterId={cp.id}
            position={cp.position}
            threat_ranges={cp.threat_ranges}
            detection_ranges={cp.detection_ranges}
            {...props}
          />
        );
      })}
    </LayerGroup>
  );
};

export default AirDefenseRangeLayer;
