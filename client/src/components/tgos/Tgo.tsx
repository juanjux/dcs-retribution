import backend from "../../api/backend";
import {
  useClearTgoDestinationMutation,
  useOpenNewTgoPackageDialogMutation,
  useOpenTgoInfoDialogMutation,
  useSetTgoDestinationMutation,
} from "../../api/liberationApi";
import { Tgo as TgoModel } from "../../api/liberationApi";
import {
  selectHighlightEmitters,
  selectHoveredEmitter,
  setHoveredEmitter,
} from "../../api/mapSlice";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { MovementPath, MovementPathHandle } from "../controlpoints/MovementPath";
import SplitLines from "../splitlines/SplitLines";
import {
  Icon,
  LatLng,
  LatLngLiteral,
  Marker as LMarker,
  Point,
} from "leaflet";
import ms from "milsymbol";
import { useCallback, useEffect, useRef, useState } from "react";
import { Marker, Tooltip } from "react-leaflet";

function iconForTgo(tgo: TgoModel) {
  const symbol = new ms.Symbol(tgo.sidc, {
    size: 24,
  });

  return new Icon({
    iconUrl: symbol.toDataURL(),
    iconAnchor: new Point(symbol.getAnchor().x, symbol.getAnchor().y),
  });
}

function metersToNauticalMiles(meters: number) {
  return meters * 0.000539957;
}

function destinationTooltipText(
  tgo: TgoModel,
  destinationish: LatLngLiteral,
  inRange: boolean
) {
  const destination = new LatLng(destinationish.lat, destinationish.lng);
  const distance = metersToNauticalMiles(
    destination.distanceTo(tgo.position)
  ).toFixed(1);
  if (!inRange) {
    return `Out of range (${distance}nm away)`;
  }
  return `${tgo.name} moving ${distance}nm next turn`;
}

function infoTooltipHtml(tgo: TgoModel) {
  const lines = [`${tgo.name} (${tgo.control_point_name})`, ...tgo.units];
  return lines.join("<br/>");
}

interface TgoProps {
  tgo: TgoModel;
}

function useTgoInteractions(tgo: TgoModel) {
  const [openNewPackageDialog] = useOpenNewTgoPackageDialogMutation();
  const [openInfoDialog] = useOpenTgoInfoDialogMutation();
  return {
    info: () => openInfoDialog({ tgoId: tgo.id }),
    newPackage: () => openNewPackageDialog({ tgoId: tgo.id }),
  };
}

/** Fixed marker: info on click, new strike package on right-click. */
function StaticTgo(props: TgoProps) {
  const dispatch = useAppDispatch();
  const interactions = useTgoInteractions(props.tgo);
  const raised = useAppSelector(
    (state) =>
      selectHighlightEmitters(state) &&
      selectHoveredEmitter(state) === props.tgo.id
  );
  return (
    <Marker
      position={props.tgo.position}
      icon={iconForTgo(props.tgo)}
      zIndexOffset={raised ? 10000 : 0}
      eventHandlers={{
        click: () => interactions.info(),
        contextmenu: () => interactions.newPackage(),
        mouseover: () =>
          dispatch(setHoveredEmitter({ id: props.tgo.id, source: "emitter" })),
        mouseout: () => dispatch(setHoveredEmitter(null)),
      }}
    >
      <Tooltip>
        {`${props.tgo.name} (${props.tgo.control_point_name})`}
        <br />
        <SplitLines items={props.tgo.units} />
      </Tooltip>
    </Marker>
  );
}

/**
 * Draggable marker for a player-owned combatant ship group. Mirrors
 * MobileControlPoint: drag to set a next-turn destination (capped range, no
 * crossing land), right-click to cancel. While a destination is set the static
 * marker (info / new package) is shown at the current position.
 */
function MovableTgoMarker(props: TgoProps) {
  // See MobileControlPoint: mutate refs during drag rather than set state, so a
  // re-render doesn't interrupt the drag.
  const markerRef = useRef<LMarker | null>(null);
  const pathRef = useRef<MovementPathHandle | null>(null);
  const dispatch = useAppDispatch();
  const interactions = useTgoInteractions(props.tgo);
  const raised = useAppSelector(
    (state) =>
      selectHighlightEmitters(state) &&
      selectHoveredEmitter(state) === props.tgo.id
  );

  const [hasDestination, setHasDestination] = useState<boolean>(
    props.tgo.destination != null
  );
  const [position, setPosition] = useState<LatLngLiteral>(
    props.tgo.destination ? props.tgo.destination : props.tgo.position
  );

  const setDestination = useCallback((destination: LatLng) => {
    setPosition(destination);
    setHasDestination(true);
  }, []);

  const resetDestination = useCallback(() => {
    setPosition(props.tgo.position);
    setHasDestination(false);
  }, [props]);

  const [putDestination, { isLoading }] = useSetTgoDestinationMutation();
  const [cancelTravel] = useClearTgoDestinationMutation();

  useEffect(() => {
    markerRef.current?.setTooltipContent(
      props.tgo.destination
        ? destinationTooltipText(props.tgo, props.tgo.destination, true)
        : infoTooltipHtml(props.tgo)
    );
  });

  return (
    <>
      <Marker
        position={position}
        icon={iconForTgo(props.tgo)}
        draggable={!isLoading}
        autoPan
        zIndexOffset={raised ? 10000 : 1000}
        opacity={props.tgo.destination ? 0.5 : 1}
        ref={(ref) => {
          if (ref != null) {
            markerRef.current = ref;
          }
        }}
        eventHandlers={{
          mouseover: () =>
            dispatch(
              setHoveredEmitter({ id: props.tgo.id, source: "emitter" })
            ),
          mouseout: () => dispatch(setHoveredEmitter(null)),
          click: () => {
            if (!hasDestination) {
              interactions.info();
            }
          },
          contextmenu: () => {
            if (props.tgo.destination) {
              cancelTravel({ tgoId: props.tgo.id }).then(() => {
                resetDestination();
              });
            } else {
              interactions.newPackage();
            }
          },
          drag: (event) => {
            const destination = event.target.getLatLng();
            backend
              .get(
                `/tgos/${props.tgo.id}/destination-in-range?lat=${destination.lat}&lng=${destination.lng}`
              )
              .then((inRange) => {
                markerRef.current?.setTooltipContent(
                  destinationTooltipText(props.tgo, destination, inRange.data)
                );
              });
            pathRef.current?.setDestination(destination);
          },
          dragend: async (event) => {
            const currentPosition = new LatLng(position.lat, position.lng);
            const destination = event.target.getLatLng();
            setDestination(destination);
            try {
              await putDestination({
                tgoId: props.tgo.id,
                body: { lat: destination.lat, lng: destination.lng },
              }).unwrap();
            } catch (error) {
              console.error("setTgoDestination failed", error);
              setDestination(currentPosition);
            }
          },
        }}
      >
        <Tooltip />
      </Marker>
      <MovementPath
        source={props.tgo.position}
        destination={position}
        ref={pathRef}
      />
    </>
  );
}

export default function Tgo(props: TgoProps) {
  if (props.tgo.blue && props.tgo.moveable) {
    return (
      <>
        <MovableTgoMarker tgo={props.tgo} key={props.tgo.destination ? 0 : 1} />
        {props.tgo.destination ? <StaticTgo tgo={props.tgo} /> : null}
      </>
    );
  }
  return <StaticTgo tgo={props.tgo} />;
}
