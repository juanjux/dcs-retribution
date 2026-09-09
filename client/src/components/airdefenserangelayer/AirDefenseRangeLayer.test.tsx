import { renderWithProviders } from "../../testutils";
import AirDefenseRangeLayer, { colorFor } from "./AirDefenseRangeLayer";
import { PropsWithChildren } from "react";

const mockLayerGroup = jest.fn();
const mockCircle = jest.fn();
jest.mock("react-leaflet", () => ({
  LayerGroup: (props: PropsWithChildren<any>) => {
    mockLayerGroup(props);
    return <>{props.children}</>;
  },
  Circle: (props: any) => {
    mockCircle(props);
  },
  Tooltip: (props: PropsWithChildren<any>) => <>{props.children}</>,
}));

describe("colorFor", () => {
  it("has a unique color for each configuration", () => {
    const params = [
      [false, false],
      [false, true],
      [true, false],
      [true, true],
    ];
    var colors = new Set<string>();
    for (const [blue, detection] of params) {
      colors.add(colorFor(blue, detection));
    }
    expect(colors.size).toEqual(4);
  });
});

describe("AirDefenseRangeLayer", () => {
  it("draws nothing when there are no TGOs", () => {
    renderWithProviders(<AirDefenseRangeLayer blue={true} />);
    expect(mockLayerGroup).toHaveBeenCalledTimes(1);
    expect(mockCircle).not.toHaveBeenCalled();
  });

  it("does not draw wrong range types", () => {
    renderWithProviders(<AirDefenseRangeLayer blue={true} />, {
      preloadedState: {
        tgos: {
          tgos: {
            foo: {
              id: "foo",
              name: "Foo",
              control_point_name: "Bar",
              category: "AA",
              blue: false,
              position: {
                lat: 0,
                lng: 0,
              },
              units: [],
              threat_ranges: [],
              detection_ranges: [20],
              dead: false,
              purchasable: true,
              sidc: "",
              task: [],
              mobile: false,
            },
          },
        },
      },
    });
    expect(mockLayerGroup).toHaveBeenCalledTimes(1);
    expect(mockCircle).not.toHaveBeenCalled();
  });

  it("draws threat ranges", () => {
    renderWithProviders(<AirDefenseRangeLayer blue={true} />, {
      preloadedState: {
        tgos: {
          tgos: {
            foo: {
              id: "foo",
              name: "Foo",
              control_point_name: "Bar",
              category: "AA",
              blue: true,
              position: {
                lat: 10,
                lng: 20,
              },
              units: [],
              threat_ranges: [10],
              detection_ranges: [20],
              dead: false,
              purchasable: true,
              sidc: "",
              task: [],
              mobile: false,
            },
          },
        },
      },
    });
    expect(mockLayerGroup).toHaveBeenCalledTimes(1);
    expect(mockCircle).toHaveBeenCalledWith(
      expect.objectContaining({
        center: {
          lat: 10,
          lng: 20,
        },
        radius: 10,
        color: colorFor(true, false),
      }),
    );
  });

  it("draws detection ranges", () => {
    renderWithProviders(<AirDefenseRangeLayer blue={true} detection />, {
      preloadedState: {
        tgos: {
          tgos: {
            foo: {
              id: "foo",
              name: "Foo",
              control_point_name: "Bar",
              category: "AA",
              blue: true,
              position: {
                lat: 10,
                lng: 20,
              },
              units: [],
              threat_ranges: [10],
              detection_ranges: [20],
              dead: false,
              purchasable: true,
              sidc: "",
              task: [],
              mobile: false,
            },
          },
        },
      },
    });
    expect(mockLayerGroup).toHaveBeenCalledTimes(1);
    expect(mockCircle).toHaveBeenCalledWith(
      expect.objectContaining({
        center: {
          lat: 10,
          lng: 20,
        },
        radius: 20,
        color: colorFor(true, true),
      }),
    );
  });

  const radarOnlyState = (blue: boolean) => ({
    tgos: {
      tgos: {
        ewr: {
          id: "ewr",
          name: "Ewr",
          control_point_name: "Bar",
          category: "AA",
          blue: blue,
          position: { lat: 10, lng: 20 },
          units: [],
          threat_ranges: [],
          detection_ranges: [300],
          dead: false,
          purchasable: true,
          sidc: "",
          task: [],
          mobile: false,
        },
      },
    },
  });

  // An EWR or a jamming site sees but does not shoot, so it has no threat ring at
  // all. It draws its detection ring on the threat layer instead, dashed, or it is
  // invisible unless you happen to have SAM detection ranges turned on.
  it("draws a radar-only site on the threat layer, dashed", () => {
    renderWithProviders(<AirDefenseRangeLayer blue={true} />, {
      preloadedState: radarOnlyState(true) as any,
    });
    expect(mockCircle).toHaveBeenCalledWith(
      expect.objectContaining({
        radius: 300,
        pathOptions: expect.objectContaining({
          color: colorFor(true, false),
          dashArray: expect.any(String),
        }),
      }),
    );
  });

  it("does not draw a radar-only site twice", () => {
    renderWithProviders(<AirDefenseRangeLayer blue={true} detection />, {
      preloadedState: radarOnlyState(true) as any,
    });
    expect(mockCircle).not.toHaveBeenCalled();
  });

  it("leaves a shooting site's threat ring solid", () => {
    renderWithProviders(<AirDefenseRangeLayer blue={true} />, {
      preloadedState: {
        tgos: {
          tgos: {
            sam: {
              id: "sam",
              name: "Sam",
              control_point_name: "Bar",
              category: "AA",
              blue: true,
              position: { lat: 10, lng: 20 },
              units: [],
              threat_ranges: [10],
              detection_ranges: [20],
              dead: false,
              purchasable: true,
              sidc: "",
              task: [],
              mobile: false,
            },
          },
        },
      } as any,
    });
    expect(mockCircle).toHaveBeenCalledWith(
      expect.objectContaining({
        radius: 10,
        pathOptions: expect.objectContaining({ dashArray: undefined }),
      }),
    );
  });

  // A jamming site carries point defence, so it has a threat ring -- a couple of
  // miles where the bubble is tens. The bubble is the circle anyone is looking for.
  it("draws a jamming bubble dashed, alongside its point defence", () => {
    renderWithProviders(<AirDefenseRangeLayer blue={true} />, {
      preloadedState: {
        tgos: {
          tgos: {
            jam: {
              id: "jam",
              name: "Jam",
              control_point_name: "Bar",
              category: "AA",
              blue: true,
              position: { lat: 10, lng: 20 },
              units: [],
              threat_ranges: [4000],
              detection_ranges: [18000],
              jamming_range: 55560,
              dead: false,
              purchasable: true,
              sidc: "",
              task: [],
              mobile: false,
            },
          },
        },
      } as any,
    });
    expect(mockCircle).toHaveBeenCalledWith(
      expect.objectContaining({
        radius: 55560,
        pathOptions: expect.objectContaining({ dashArray: expect.any(String) }),
      }),
    );
    expect(mockCircle).toHaveBeenCalledWith(
      expect.objectContaining({
        radius: 4000,
        pathOptions: expect.objectContaining({ dashArray: undefined }),
      }),
    );
  });
});
