import { UnculledZone } from "../../api/liberationApi";
import { selectUnculledZones } from "../../api/unculledZonesSlice";
import { useAppSelector } from "../../app/hooks";
import { LayerGroup, Circle } from "react-leaflet";

interface CullingExclusionCirclesProps {
  zones: UnculledZone[];
}

const CullingExclusionCircles = (props: CullingExclusionCirclesProps) => {
  return (
    <>
      <LayerGroup>
        {props.zones.map((zone, idx) => {
          return (
            <Circle
              key={idx}
              center={zone.position}
              radius={zone.radius}
              color="#b4ff8c"
              fill={false}
              interactive={false}
            />
          );
        })}
      </LayerGroup>
    </>
  );
};

// Raw-layer variant (no LayersControl.Overlay) for the custom map layers panel.
export function CullingExclusionLayer() {
  const data = useAppSelector(selectUnculledZones).zones;
  return <CullingExclusionCircles zones={data} />;
}
