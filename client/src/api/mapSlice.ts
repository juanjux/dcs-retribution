import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { PayloadAction, createSlice } from "@reduxjs/toolkit";
import { LatLngLiteral } from "leaflet";

// Where a hover originated: the emitter's icon, or one of its range rings. The
// highlight is symmetric (hovering either lights up the other), but we draw a
// different cue depending on the source: hovering a ring marks the emitter with
// a blob so you can find it; hovering the emitter only lights up its ring.
export type EmitterHoverSource = "emitter" | "ring";

interface MapState {
  center: LatLngLiteral;
  // Id of the TGO/control point whose air-defense ring (or icon) is currently
  // hovered, so its icon can be raised above overlapping ones while highlighted.
  hoveredEmitterId: string | null;
  // What was hovered to set hoveredEmitterId (icon vs. ring).
  hoveredEmitterSource: EmitterHoverSource | null;
  // Whether the hover highlight (ring <-> emitter) is enabled. Toggled from
  // the map's layer control.
  highlightEmitters: boolean;
  // Whether fully-destroyed, non-repairable ground objects (buildings, ships,
  // ...) are shown on the map, per coalition. Toggled from the map's layer
  // control; defaults to shown. Repairable objects (SAM/EWR/armor) are never
  // hidden by this.
  showDestroyedNonRepairable: { blue: boolean; red: boolean };
}

const initialState: MapState = {
  center: { lat: 0, lng: 0 },
  hoveredEmitterId: null,
  hoveredEmitterSource: null,
  highlightEmitters: true,
  showDestroyedNonRepairable: { blue: true, red: true },
};

const mapSlice = createSlice({
  name: "map",
  initialState: initialState,
  reducers: {
    setHoveredEmitter(
      state,
      action: PayloadAction<{ id: string; source: EmitterHoverSource } | null>
    ) {
      state.hoveredEmitterId = action.payload?.id ?? null;
      state.hoveredEmitterSource = action.payload?.source ?? null;
    },
    setHighlightEmitters(state, action: PayloadAction<boolean>) {
      state.highlightEmitters = action.payload;
    },
    setShowDestroyedNonRepairable(
      state,
      action: PayloadAction<{ blue: boolean; value: boolean }>
    ) {
      if (action.payload.blue) {
        state.showDestroyedNonRepairable.blue = action.payload.value;
      } else {
        state.showDestroyedNonRepairable.red = action.payload.value;
      }
    },
  },
  extraReducers: (builder) => {
    builder.addCase(gameLoaded, (state, action) => {
      if (action.payload.map_center != null) {
        state.center = action.payload.map_center;
      }
    });
    builder.addCase(gameUnloaded, (state) => {
      state.center = { lat: 0, lng: 0 };
      state.hoveredEmitterId = null;
      state.hoveredEmitterSource = null;
    });
  },
});

export const {
  setHoveredEmitter,
  setHighlightEmitters,
  setShowDestroyedNonRepairable,
} = mapSlice.actions;

export const selectMapCenter = (state: RootState) => state.map.center;
export const selectHoveredEmitter = (state: RootState) =>
  state.map.hoveredEmitterId;
export const selectHoveredEmitterSource = (state: RootState) =>
  state.map.hoveredEmitterSource;
export const selectHighlightEmitters = (state: RootState) =>
  state.map.highlightEmitters;
export const selectShowDestroyedNonRepairable = (state: RootState) =>
  state.map.showDestroyedNonRepairable;

export default mapSlice.reducer;
