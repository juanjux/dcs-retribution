import { selectControlPoints } from "../../api/controlPointsSlice";
import { selectTgos } from "../../api/tgosSlice";
import { useAppSelector } from "../../app/hooks";
import { LatLng } from "../../api/liberationApi";
import { Circle, LayerGroup } from "react-leaflet";

interface RangeCirclesProps {
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

const RangeCircles = (props: RangeCirclesProps) => {
  const radii = props.detection
    ? props.detection_ranges
    : props.threat_ranges;
  const color = colorFor(props.blue, props.detection === true);
  const weight = props.detection ? 1 : 2;

  return (
    <>
      {radii.map((radius, idx) => {
        return (
          <Circle
            key={idx}
            center={props.position}
            radius={radius}
            color={color}
            fill={false}
            weight={weight}
            interactive={false}
          />
        );
      })}
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
