import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { PayloadAction, createSlice } from "@reduxjs/toolkit";
import { LatLngLiteral } from "leaflet";

interface MapState {
  center: LatLngLiteral;
  // Whether fully-destroyed, non-repairable ground objects (buildings, ships,
  // ...) are shown on the map, per coalition. Toggled from the map's layer
  // control; defaults to shown. Repairable objects (SAM/EWR/armor) are never
  // hidden by this.
  showDestroyedNonRepairable: { blue: boolean; red: boolean };
}

const initialState: MapState = {
  center: { lat: 0, lng: 0 },
  showDestroyedNonRepairable: { blue: true, red: true },
};

const mapSlice = createSlice({
  name: "map",
  initialState: initialState,
  reducers: {
    setShowDestroyedNonRepairable(
      state,
      action: PayloadAction<{ blue: boolean; value: boolean }>,
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
    });
  },
});

export const { setShowDestroyedNonRepairable } = mapSlice.actions;

export const selectMapCenter = (state: RootState) => state.map.center;
export const selectShowDestroyedNonRepairable = (state: RootState) =>
  state.map.showDestroyedNonRepairable;

export default mapSlice.reducer;
