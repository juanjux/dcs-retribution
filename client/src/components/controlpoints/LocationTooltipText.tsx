import SplitLines from "../splitlines/SplitLines";

interface LocationTooltipTextProps {
  name: string;
  tacan?: string | null;
  atcFrequency?: string | null;
  units?: string[];
}

export const LocationTooltipText = (props: LocationTooltipTextProps) => {
  return (
    <>
      <h3 style={{ margin: 0 }}>{props.name}</h3>
      {props.atcFrequency && (
        <div style={{ marginTop: 2 }}>ATC: {props.atcFrequency}</div>
      )}
      {props.tacan && <div>TACAN: {props.tacan}</div>}
      {props.units && props.units.length > 0 && (
        <SplitLines items={props.units} />
      )}
    </>
  );
};

export default LocationTooltipText;
