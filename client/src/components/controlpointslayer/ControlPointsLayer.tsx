import { selectControlPoints } from "../../api/controlPointsSlice";
import { selectShowDestroyedNonRepairable } from "../../api/mapSlice";
import { useAppSelector } from "../../app/hooks";
import ControlPoint from "../controlpoints";
import { LayerGroup } from "react-leaflet";

export default function ControlPointsLayer() {
  const controlPoints = useAppSelector(selectControlPoints);
  const showDestroyed = useAppSelector(selectShowDestroyedNonRepairable);
  return (
    <LayerGroup>
      {Object.values(controlPoints.controlPoints)
        .filter((controlPoint) => {
          // A fully-destroyed carrier/LHA group is a non-repairable naval loss; hide it
          // when that coalition's "destroyed (non-repairable)" layer is off, mirroring
          // how TgosLayer hides destroyed naval TGOs. (dead is only ever true for
          // carrier/LHA control points, never for airfields/FOBs.)
          if (controlPoint.dead) {
            return controlPoint.blue ? showDestroyed.blue : showDestroyed.red;
          }
          return true;
        })
        .map((controlPoint) => {
          return (
            <ControlPoint key={controlPoint.id} controlPoint={controlPoint} />
          );
        })}
    </LayerGroup>
  );
}
