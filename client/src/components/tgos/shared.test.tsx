import { Tgo as TgoModel } from "../../api/liberationApi";
import { iconForTgo, isFullyDeadRepairing } from "./shared";

// APP-6(D) SIDC with the status/condition digit (index 6) parameterised.
function sidc(status: string): string {
  return "100310" + status + "0001301000000";
}

function fakeTgo(dead: boolean, status: string): TgoModel {
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
    sidc: sidc(status),
    task: [],
    mobile: false,
  } as unknown as TgoModel;
}

describe("isFullyDeadRepairing", () => {
  it("is true only when the whole group is dead and the bar is 'damaged' (repairing)", () => {
    expect(isFullyDeadRepairing(fakeTgo(true, "3"))).toBe(true); // dead + damaged
    expect(isFullyDeadRepairing(fakeTgo(true, "4"))).toBe(false); // dead + destroyed
    expect(isFullyDeadRepairing(fakeTgo(false, "3"))).toBe(false); // partial damage
    expect(isFullyDeadRepairing(fakeTgo(false, "2"))).toBe(false); // fully capable
  });
});

describe("iconForTgo health-bar colour", () => {
  it("recolours the yellow damaged bar to orange for a fully-dead repairing group", () => {
    const url = iconForTgo(fakeTgo(true, "3")).options.iconUrl ?? "";
    const svg = decodeURIComponent(url.slice(url.indexOf(",") + 1));
    expect(svg).toContain("rgb(255,140,0)"); // orange bar
    expect(svg).not.toContain("rgb(255,255,0)"); // no leftover yellow
  });

  it("leaves the yellow bar for a partially-damaged group", () => {
    const url = iconForTgo(fakeTgo(false, "3")).options.iconUrl ?? "";
    // partial damage keeps milsymbol's default icon — not recoloured.
    const svg = decodeURIComponent(url.slice(url.indexOf(",") + 1));
    expect(svg).toContain("rgb(255,255,0)"); // still yellow
    expect(svg).not.toContain("rgb(255,140,0)");
  });
});
