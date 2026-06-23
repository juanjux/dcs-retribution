import { selectControlPoints } from "../../api/controlPointsSlice";
import { selectTgos } from "../../api/tgosSlice";
import {
  selectHighlightEmitters,
  selectHoveredEmitter,
  selectHoveredEmitterSource,
  setHoveredEmitter,
} from "../../api/mapSlice";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import {
  LatLng,
  useOpenNewTgoPackageDialogMutation,
  useOpenTgoInfoDialogMutation,
} from "../../api/liberationApi";
import { Fragment } from "react";
import { Circle, CircleMarker, LayerGroup, Tooltip } from "react-leaflet";

interface RangeCirclesProps {
  emitterId: string;
  name: string;
  units: string[];
  position: LatLng;
  threat_ranges: number[];
  detection_ranges: number[];
  blue: boolean;
  detection?: boolean;
  // When set, clicking the ring opens the emitter's info dialog (same as
  // clicking its map icon). Lets you reach a SAM site whose icon is buried
  // under another. Off for carrier/LHA rings, whose emitterId is a
  // control-point id rather than a TGO id.
  selectable?: boolean;
}

export function colorFor(blue: boolean, detection: boolean) {
  if (blue) {
    return detection ? "#bb89ff" : "#0084ff";
  }
  return detection ? "#eee17b" : "#c85050";
}

// Bright colour used to mark the hovered ring and its emitter.
const HIGHLIGHT_COLOR = "#ffff00";

// Collapse a unit list like ["SA-6 TEL", "SA-6 TEL", "Straight Flush"] into
// ["2x SA-6 TEL", "Straight Flush"] so the ring tooltip names the SAM compactly.
function summarizeUnits(units: string[]): string[] {
  const counts = new Map<string, number>();
  units.forEach((unit) => counts.set(unit, (counts.get(unit) ?? 0) + 1));
  return Array.from(counts, ([name, n]) => (n > 1 ? `${n}x ${name}` : name));
}

const RangeCircles = (props: RangeCirclesProps) => {
  const radii = props.detection ? props.detection_ranges : props.threat_ranges;
  const color = colorFor(props.blue, props.detection === true);
  const baseWeight = props.detection ? 1 : 2;
  const dispatch = useAppDispatch();

  // Highlight when the feature is enabled and this emitter is the hovered one.
  // Driven by shared state, so hovering either the ring or the emitter's icon
  // lights up the other (and the icon is raised).
  const highlighted = useAppSelector(
    (state) =>
      selectHighlightEmitters(state) &&
      selectHoveredEmitter(state) === props.emitterId,
  );
  // Only mark the emitter with a blob when the hover came from a ring (to help
  // locate the emitter, associating ring <-> emitter). When the emitter icon
  // itself is hovered we don't blob it, since we're already pointing at it. The
  // ring itself always lights up while highlighted, in either direction.
  const markEmitter = useAppSelector(
    (state) => highlighted && selectHoveredEmitterSource(state) === "ring",
  );

  const [openTgoInfoDialog] = useOpenTgoInfoDialogMutation();
  const [openNewPackageDialog] = useOpenNewTgoPackageDialogMutation();

  const hover = {
    mouseover: () =>
      dispatch(setHoveredEmitter({ id: props.emitterId, source: "ring" })),
    mouseout: () => dispatch(setHoveredEmitter(null)),
  };
  // The ring mirrors the emitter icon's clicks, so you can reach a site whose
  // icon is buried under another: left-click opens its info dialog, right-click
  // starts a new package against it.
  const ringHandlers = props.selectable
    ? {
        ...hover,
        click: () => openTgoInfoDialog({ tgoId: props.emitterId }),
        contextmenu: () => openNewPackageDialog({ tgoId: props.emitterId }),
      }
    : hover;

  return (
    <>
      {radii.map((radius, idx) => (
        <Fragment key={idx}>
          <Circle
            center={props.position}
            radius={radius}
            // Style goes through pathOptions (not bare color/weight props):
            // react-leaflet only re-applies setStyle when pathOptions changes,
            // so bare props would be set once at creation and never update when
            // the highlight toggles.
            pathOptions={{
              color: highlighted ? HIGHLIGHT_COLOR : color,
              weight: highlighted ? baseWeight + 2 : baseWeight,
              fill: false,
            }}
            interactive={false}
          />
          {/* Invisible wide ring that catches the hover. The visible stroke is
              a fixed pixel width so it gets hard to hit when zoomed out; this
              18px transparent band (pointer-events: stroke via the className,
              so it works despite being invisible) gives a comfortable target
              along the perimeter without filling the disc. */}
          <Circle
            center={props.position}
            radius={radius}
            color={color}
            fill={false}
            opacity={0}
            weight={18}
            className="air-defense-ring-hit"
            eventHandlers={ringHandlers}
          >
            <Tooltip sticky className="tooltip-delayed">
              <b>{props.name}</b>
              {summarizeUnits(props.units).map((unit, i) => (
                <div key={i}>{unit}</div>
              ))}
            </Tooltip>
          </Circle>
        </Fragment>
      ))}
      {markEmitter && (
        <CircleMarker
          center={props.position}
          radius={20}
          color={HIGHLIGHT_COLOR}
          fillColor={HIGHLIGHT_COLOR}
          fillOpacity={0.5}
          weight={4}
          interactive={false}
          // Draw above the marker icons (markerPane, z 600) so the highlight is
          // not buried under a cluster of overlapping unit icons.
          pane="tooltipPane"
        />
      )}
    </>
  );
};

interface AirDefenseRangeLayerProps {
  blue: boolean;
  detection?: boolean;
}

export const AirDefenseRangeLayer = (props: AirDefenseRangeLayerProps) => {
  const tgos = Object.values(useAppSelector(selectTgos).tgos).filter(
    (tgo) => tgo.blue === props.blue,
  );
  // Carrier/LHA control points carry their air-defense ranges (from the
  // surviving escort ships) directly, since their ship group is not emitted as
  // a standalone TGO. Draw their rings here too so a battered carrier group
  // does not look defenceless on the map.
  const controlPoints = Object.values(
    useAppSelector(selectControlPoints).controlPoints,
  ).filter((cp) => cp.blue === props.blue);

  return (
    <LayerGroup>
      {tgos.map((tgo) => {
        return (
          <RangeCircles
            key={tgo.id}
            emitterId={tgo.id}
            name={tgo.name}
            units={tgo.units}
            position={tgo.position}
            threat_ranges={tgo.threat_ranges}
            detection_ranges={tgo.detection_ranges}
            selectable
            {...props}
          />
        );
      })}
      {controlPoints.map((cp) => {
        return (
          <RangeCircles
            key={cp.id}
            emitterId={cp.id}
            name={cp.name}
            units={cp.units}
            position={cp.position}
            threat_ranges={cp.threat_ranges}
            detection_ranges={cp.detection_ranges}
            {...props}
          />
        );
      })}
    </LayerGroup>
  );
};

export default AirDefenseRangeLayer;
