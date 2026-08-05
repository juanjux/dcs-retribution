import { Tgo as TgoModel } from "../../api/liberationApi";
import { iconForTgo, isRepairing } from "./shared";

// APP-6(D) SIDC with the status/condition digit (index 6) parameterised.
function sidc(status: string): string {
  return "100310" + status + "0001301000000";
}

function fakeTgo(dead: boolean, status: string, repairing: boolean): TgoModel {
  return {
    id: "id",
    name: "SAM",
    control_point_name: "CP",
    category: "aa",
    blue: true,
    position: { lat: 0, lng: 0 },
    units: [],
    threat_ranges: [],
    detection_ranges: [],
    dead,
    purchasable: true,
    repairing,
    sidc: sidc(status),
    task: [],
    mobile: false,
  } as unknown as TgoModel;
}

describe("isRepairing", () => {
  it("is true whenever repairs are pending and the bar is 'damaged'", () => {
    expect(isRepairing(fakeTgo(true, "3", true))).toBe(true); // fully dead + repairing
    expect(isRepairing(fakeTgo(false, "3", true))).toBe(true); // partial damage + repairing
    expect(isRepairing(fakeTgo(false, "3", false))).toBe(false); // damaged, not repairing (yellow)
    expect(isRepairing(fakeTgo(true, "4", false))).toBe(false); // dead, unrepaired (red)
    expect(isRepairing(fakeTgo(false, "2", false))).toBe(false); // fully capable (green)
  });
});

describe("iconForTgo health-bar colour", () => {
  it("recolours the yellow damaged bar to orange for a fully-dead repairing group", () => {
    const url = iconForTgo(fakeTgo(true, "3", true)).options.iconUrl ?? "";
    const svg = decodeURIComponent(url.slice(url.indexOf(",") + 1));
    expect(svg).toContain("rgb(255,140,0)"); // orange bar
    expect(svg).not.toContain("rgb(255,255,0)"); // no leftover yellow
  });

  it("recolours to orange for a PARTIALLY damaged repairing group too", () => {
    const url = iconForTgo(fakeTgo(false, "3", true)).options.iconUrl ?? "";
    const svg = decodeURIComponent(url.slice(url.indexOf(",") + 1));
    expect(svg).toContain("rgb(255,140,0)");
    expect(svg).not.toContain("rgb(255,255,0)");
  });

  it("keeps the yellow bar for damage with no repairs pending", () => {
    const url = iconForTgo(fakeTgo(false, "3", false)).options.iconUrl ?? "";
    // No repairs pending: milsymbol's default icon, not recoloured.
    const svg = decodeURIComponent(url.slice(url.indexOf(",") + 1));
    expect(svg).toContain("rgb(255,255,0)"); // still yellow
    expect(svg).not.toContain("rgb(255,140,0)");
  });
});
