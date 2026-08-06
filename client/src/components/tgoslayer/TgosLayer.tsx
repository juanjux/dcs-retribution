import { selectShowDestroyedNonRepairable } from "../../api/mapSlice";
import { selectTgos } from "../../api/tgosSlice";
import { useAppSelector } from "../../app/hooks";
import Tgo from "../tgos/Tgo";
import { LayerGroup } from "react-leaflet";

interface TgosLayerProps {
  categories?: string[];
  exclude?: true;
  task?: string;
}

export default function TgosLayer(props: TgosLayerProps) {
  const allTgos = Object.values(useAppSelector(selectTgos).tgos);
  const showDestroyed = useAppSelector(selectShowDestroyedNonRepairable);
  const categoryFilter = props.categories ?? [];
  const taskFilter = props.task ?? "";
  const tgos = allTgos.filter((tgo) => {
    // Hide fully-destroyed, non-rebuildable objects (buildings, ships, ...) when
    // that coalition's "destroyed (non-repairable)" layer is turned off.
    // Repairable objects (purchasable: SAM/EWR/armor) are never hidden by this.
    if (tgo.dead && !tgo.purchasable) {
      const shown = tgo.blue ? showDestroyed.blue : showDestroyed.red;
      if (!shown) {
        return false;
      }
    }
    if (taskFilter && tgo.task) {
      return taskFilter === tgo.task[0];
    }
    return categoryFilter.includes(tgo.category) === !(props.exclude ?? false);
  });
  return (
    <LayerGroup>
      {tgos.map((tgo) => {
        return <Tgo key={tgo.name} tgo={tgo} />;
      })}
    </LayerGroup>
  );
}
