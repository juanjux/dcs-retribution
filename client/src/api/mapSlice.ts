import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { PayloadAction, createSlice } from "@reduxjs/toolkit";
import { LatLngLiteral } from "leaflet";

interface MapState {
  center: LatLngLiteral;
  // Id of the TGO/control point whose air-defense ring is currently hovered,
  // so its icon can be raised above overlapping ones while highlighted.
  hoveredEmitterId: string | null;
  // Whether the hover highlight (ring <-> emitter) is enabled. Toggled from
  // the map's layer control.
  highlightEmitters: boolean;
}

const initialState: MapState = {
  center: { lat: 0, lng: 0 },
  hoveredEmitterId: null,
  highlightEmitters: true,
};

const mapSlice = createSlice({
  name: "map",
  initialState: initialState,
  reducers: {
    setHoveredEmitter(state, action: PayloadAction<string | null>) {
      state.hoveredEmitterId = action.payload;
    },
    setHighlightEmitters(state, action: PayloadAction<boolean>) {
      state.highlightEmitters = action.payload;
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
    });
  },
});

export const { setHoveredEmitter, setHighlightEmitters } = mapSlice.actions;

export const selectMapCenter = (state: RootState) => state.map.center;
export const selectHoveredEmitter = (state: RootState) =>
  state.map.hoveredEmitterId;
export const selectHighlightEmitters = (state: RootState) =>
  state.map.highlightEmitters;

export default mapSlice.reducer;
