import {
  type Map as LibreMap,
  type LngLatLike,
  type MapGeoJSONFeature,
  Popup,
} from "maplibre-gl";
import type { MapLabels } from "./types";

// A context tile is not a catalogue identity or a proven project association.
export function showWorldBuilding(
  map: LibreMap,
  point: LngLatLike,
  feature: MapGeoJSONFeature,
  labels: MapLabels,
  locale: string,
) {
  const root = document.createElement("div");
  root.className = "building-context";
  const title = document.createElement("strong");
  title.textContent = labels.building;
  const height = document.createElement("p");
  const metres = Number(feature.properties.render_height);
  height.textContent = `${labels.heightIndicative} : ${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(metres)} m`;
  const source = document.createElement("a");
  source.href = "https://www.openstreetmap.org/copyright";
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  source.textContent = "© OpenStreetMap · OpenFreeMap ↗";
  root.append(title, height, source);
  const popup = new Popup({
    maxWidth: "250px",
    closeButton: false,
    closeOnMove: true,
  })
    .setLngLat(point)
    .setDOMContent(root)
    .addTo(map);
  root.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      popup.remove();
      map.getCanvas().focus();
    }
  });
  return popup;
}
