import { UiIcon } from "./ui-icon";

export function MapLocateButton({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <button className="map-locate-button" type="button" onClick={onClick}>
      <UiIcon name="map" />
      {label}
    </button>
  );
}
