interface LocationTooltipTextProps {
  name: string;
  tacan?: string | null;
  atcFrequency?: string | null;
}

export const LocationTooltipText = (props: LocationTooltipTextProps) => {
  return (
    <>
      <h3 style={{ margin: 0 }}>{props.name}</h3>
      {props.atcFrequency && (
        <div style={{ marginTop: 2 }}>ATC: {props.atcFrequency}</div>
      )}
      {props.tacan && <div>TACAN: {props.tacan}</div>}
    </>
  );
};

export default LocationTooltipText;
