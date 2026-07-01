import { Tgo as TgoModel } from "../../api/liberationApi";
import { setShowDestroyedNonRepairable } from "../../api/mapSlice";
import { setupStore } from "../../app/store";
import { renderWithProviders } from "../../testutils";
import TgosLayer from "./TgosLayer";
import { PropsWithChildren } from "react";

const mockTgo = jest.fn();
jest.mock("react-leaflet", () => ({
  LayerGroup: (props: PropsWithChildren<any>) => {
    return <>{props.children}</>;
  },
}));
jest.mock("../tgos/Tgo", () => (props: { tgo: TgoModel }) => {
  mockTgo(props.tgo);
  return null;
});

function fakeTgo(o: {
  id: string;
  blue: boolean;
  dead: boolean;
  purchasable: boolean;
  category: string;
}): TgoModel {
  return {
    id: o.id,
    name: o.id,
    control_point_name: "CP",
    category: o.category,
    blue: o.blue,
    position: { lat: 0, lng: 0 },
    units: [],
    threat_ranges: [],
    detection_ranges: [],
    dead: o.dead,
    purchasable: o.purchasable,
    sidc: "",
  };
}

// Build a store seeded with the given TGOs and per-side "show destroyed"
// flags. The flags are set by dispatching (rather than via a full preloaded
// map-slice literal) so the test stays valid even as MapState gains fields.
function storeWith(tgos: TgoModel[], showRed: boolean, showBlue: boolean) {
  const store = setupStore({
    tgos: { tgos: Object.fromEntries(tgos.map((t) => [t.id, t])) },
  });
  store.dispatch(
    setShowDestroyedNonRepairable({ blue: false, value: showRed }),
  );
  store.dispatch(
    setShowDestroyedNonRepairable({ blue: true, value: showBlue }),
  );
  return store;
}

describe("TgosLayer destroyed (non-repairable) filter", () => {
  beforeEach(() => mockTgo.mockClear());

  it("hides dead non-repairable objects when that side's layer is off", () => {
    const ship = fakeTgo({
      id: "ship",
      blue: false,
      dead: true,
      purchasable: false,
      category: "ship",
    });
    renderWithProviders(<TgosLayer categories={["ship"]} />, {
      store: storeWith([ship], false, true),
    });
    expect(mockTgo).not.toHaveBeenCalled();
  });

  it("shows them when that side's layer is on", () => {
    const ship = fakeTgo({
      id: "ship",
      blue: false,
      dead: true,
      purchasable: false,
      category: "ship",
    });
    renderWithProviders(<TgosLayer categories={["ship"]} />, {
      store: storeWith([ship], true, true),
    });
    expect(mockTgo).toHaveBeenCalledTimes(1);
  });

  it("never hides repairable (purchasable) objects, even when dead", () => {
    const sam = fakeTgo({
      id: "sam",
      blue: false,
      dead: true,
      purchasable: true,
      category: "aa",
    });
    renderWithProviders(<TgosLayer categories={["aa"]} />, {
      store: storeWith([sam], false, false),
    });
    expect(mockTgo).toHaveBeenCalledTimes(1);
  });

  it("does not hide living non-repairable objects", () => {
    const ship = fakeTgo({
      id: "ship",
      blue: false,
      dead: false,
      purchasable: false,
      category: "ship",
    });
    renderWithProviders(<TgosLayer categories={["ship"]} />, {
      store: storeWith([ship], false, true),
    });
    expect(mockTgo).toHaveBeenCalledTimes(1);
  });

  it("only hides the side whose layer is off", () => {
    const redShip = fakeTgo({
      id: "red",
      blue: false,
      dead: true,
      purchasable: false,
      category: "ship",
    });
    const blueShip = fakeTgo({
      id: "blue",
      blue: true,
      dead: true,
      purchasable: false,
      category: "ship",
    });
    renderWithProviders(<TgosLayer categories={["ship"]} />, {
      store: storeWith([redShip, blueShip], false, true),
    });
    expect(mockTgo).toHaveBeenCalledTimes(1);
    expect(mockTgo).toHaveBeenCalledWith(
      expect.objectContaining({ id: "blue" }),
    );
  });
});
