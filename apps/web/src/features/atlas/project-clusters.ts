import type {
  GeoJSONSource,
  Map as LibreMap,
  MapMouseEvent,
} from "maplibre-gl";
import { clusteredProjects } from "./map-analysis";
import { PROJECT_MARKER_FILTER, PROJECT_MARKER_IMAGE } from "./map-markers";
import type { AtlasContext } from "./types";

export const PROJECT_CLUSTER_LAYERS = [
  "cluster-projects",
  "single-project",
  "close-project",
];
const project = PROJECT_MARKER_FILTER;
export function updateProjectClusters(
  map: LibreMap,
  context: AtlasContext | null,
  visible = true,
  names = true,
) {
  if (!map.getSource("place")) return;
  if (!map.getSource("project-clusters")) {
    map.addSource("project-clusters", {
      type: "geojson",
      data: clusteredProjects(context),
      cluster: true,
      clusterMaxZoom: 13,
      clusterRadius: 44,
    });
    map.addLayer({
      id: "cluster-projects",
      type: "circle",
      source: "project-clusters",
      maxzoom: 14,
      filter: ["has", "point_count"],
      paint: {
        "circle-color": "#123e46",
        "circle-radius": ["step", ["get", "point_count"], 19, 10, 23, 50, 28],
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });
    map.addLayer({
      id: "cluster-count",
      type: "symbol",
      source: "project-clusters",
      maxzoom: 14,
      filter: ["has", "point_count"],
      layout: {
        "text-field": ["get", "point_count_abbreviated"],
        "text-font": ["Arial", "Noto Sans", "sans-serif"],
        "text-size": 12,
      },
      paint: { "text-color": "#ffffff" },
    });
    for (const [id, source, minzoom, maxzoom] of [
      ["single-project", "project-clusters", 0, 14],
      ["close-project", "place", 14, 24],
    ] as const) {
      map.addLayer({
        id,
        type: "symbol",
        source,
        minzoom,
        maxzoom,
        filter:
          id === "single-project" ? ["!", ["has", "point_count"]] : project,
        layout: {
          "icon-image": PROJECT_MARKER_IMAGE,
          "icon-size": 1.12,
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
          "icon-pitch-alignment": "viewport",
          "icon-rotation-alignment": "viewport",
        },
      });
    }
    // Keep other places independent: a cluster count always means unique projects.
    if (map.getLayer("project-halo"))
      map.setLayerZoomRange("project-halo", 14, 24);
    if (map.getLayer("project-names"))
      map.setLayerZoomRange("project-names", 14, 24);
  } else
    (map.getSource("project-clusters") as GeoJSONSource).setData(
      clusteredProjects(context),
    );
  for (const id of [...PROJECT_CLUSTER_LAYERS, "cluster-count"])
    map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
  if (map.getLayer("project-names"))
    map.setLayoutProperty(
      "project-names",
      "visibility",
      visible && names ? "visible" : "none",
    );
}
export function zoomProjectCluster(map: LibreMap, event: MapMouseEvent) {
  if (!map.getLayer("cluster-projects")) return false;
  const cluster = map.queryRenderedFeatures(event.point, {
    layers: ["cluster-projects"],
  })[0];
  if (cluster?.geometry.type !== "Point") return false;
  const center = cluster.geometry.coordinates as [number, number];
  const source = map.getSource("project-clusters") as GeoJSONSource;
  void source
    .getClusterExpansionZoom(Number(cluster.properties.cluster_id))
    .then((zoom) => {
      if (!map.getSource("project-clusters")) return;
      map.easeTo({
        center,
        zoom,
        duration: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? 0
          : 300,
      });
    })
    .catch(() => {});
  return true;
}
