import { setShowDestroyedNonRepairable } from "../../api/mapSlice";
import { useAppDispatch } from "../../app/hooks";
import { LayerGroup } from "react-leaflet";

interface DestroyedTgoToggleProps {
  blue: boolean;
}

// Empty layer wrapped in a LayersControl.Overlay. Toggling the overlay adds or
// removes this (otherwise invisible) layer, which we use to show/hide that
// coalition's fully-destroyed, non-repairable ground objects (the actual
// filtering happens in TgosLayer based on the dispatched flag).
export default function DestroyedTgoToggle(props: DestroyedTgoToggleProps) {
  const dispatch = useAppDispatch();
  return (
    <LayerGroup
      eventHandlers={{
        add: () =>
          dispatch(
            setShowDestroyedNonRepairable({ blue: props.blue, value: true }),
          ),
        remove: () =>
          dispatch(
            setShowDestroyedNonRepairable({ blue: props.blue, value: false }),
          ),
      }}
    />
  );
}
