import { setHighlightEmitters } from "../../api/mapSlice";
import { useAppDispatch } from "../../app/hooks";
import { LayerGroup } from "react-leaflet";

// Empty layer wrapped in a LayersControl.Overlay. Toggling the overlay adds or
// removes this (otherwise invisible) layer, which we use to enable/disable the
// "highlight radar emitter on hover" behaviour.
export default function EmitterHighlightToggle() {
  const dispatch = useAppDispatch();
  return (
    <LayerGroup
      eventHandlers={{
        add: () => dispatch(setHighlightEmitters(true)),
        remove: () => dispatch(setHighlightEmitters(false)),
      }}
    />
  );
}
