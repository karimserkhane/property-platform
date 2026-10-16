"use client";

import { Map as LibreMap, NavigationControl, setWorkerUrl } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { mapControlLabels, mapLayers, mapName } from "../atlas/map-style";
import type { MapContext, MapLabels } from "../atlas/types";
import {
  neighbourhoodContextBounds,
  projectLocationBounds,
} from "./neighbourhood-focus";
import styles from "./project.module.css";
import type { ProjectMapLocation } from "./types";
import "maplibre-gl/dist/maplibre-gl.css";

setWorkerUrl(
  new URL(
    "maplibre-gl/dist/maplibre-gl-worker.mjs",
    import.meta.url,
  ).toString(),
);

export default function NeighbourhoodMap({
  territory,
  bounds,
  locations,
  locale,
  label,
  mapLabels,
  unavailable,
}: {
  territory: string;
  bounds: number[];
  locations: ProjectMapLocation[];
  locale: string;
  label: string;
  mapLabels: MapLabels;
  unavailable: string;
}) {
  const root = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!root.current) return;
    const abort = new AbortController();
    let map: LibreMap | undefined;
    let resize: ResizeObserver | undefined;
    setFailed(false);
    const extent: [[number, number], [number, number]] = [
      [bounds[0], bounds[1]],
      [bounds[2], bounds[3]],
    ];
    const projectExtent = projectLocationBounds(locations, bounds);
    const queryBounds = neighbourhoodContextBounds(projectExtent, bounds);
    const search = new URLSearchParams({
      territory,
      bbox: queryBounds.join(","),
    });
    void fetch(`/api/atlas/map-context?${search}`, {
      signal: AbortSignal.any([abort.signal, AbortSignal.timeout(10000)]),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("unavailable");
        return (await response.json()) as MapContext;
      })
      .then((data) => {
        if (abort.signal.aborted || !root.current) return;
        const projectFeatures = projectExtent
          ? locations.map((location) => ({
              type: "Feature" as const,
              id: location.id,
              geometry: location.geometry,
              properties: { name: location.name, name_ar: "" },
            }))
          : [];
        map = new LibreMap({
          container: root.current,
          ...(projectExtent &&
          projectExtent[0][0] === projectExtent[1][0] &&
          projectExtent[0][1] === projectExtent[1][1]
            ? { center: projectExtent[0], zoom: 16.5 }
            : {
                bounds: projectExtent ?? extent,
                fitBoundsOptions: {
                  padding: 64,
                  maxZoom: projectExtent ? 16.5 : 14,
                  animate: false,
                },
              }),
          maxBounds: extent,
          scrollZoom: false,
          minZoom: 10,
          maxZoom: 19,
          locale: mapControlLabels(mapLabels, label),
          style: {
            version: 8,
            sources: {},
            layers: [
              {
                id: "water",
                type: "background",
                paint: { "background-color": "#c9dde0" },
              },
            ],
          },
        });
        map.addControl(
          new NavigationControl({ showCompass: false }),
          "top-right",
        );
        resize = new ResizeObserver(() => map?.resize());
        resize.observe(root.current);
        map
          .getCanvas()
          .addEventListener("webglcontextlost", () => setFailed(true), {
            signal: abort.signal,
          });
        map.on("load", () => {
          if (!map) return;
          for (const [key, collection] of Object.entries(data))
            map.addSource(key, {
              type: "geojson",
              data: collection,
              attribution:
                key === "building"
                  ? '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors · ODbL</a> · DMT / Onwani'
                  : undefined,
            });
          for (const layer of mapLayers(locale).filter((layer) =>
            [
              "land",
              "areas",
              "buildings",
              "street-casing",
              "streets",
              "street-names",
              "places",
              "place-names",
            ].includes(layer.id),
          )) {
            // Keep the neighbourhood legible while the current project owns the accent.
            if (layer.id === "buildings" && layer.type === "fill")
              layer.paint = {
                ...layer.paint,
                "fill-color": "#bcc7c2",
                "fill-opacity": 0.6,
                "fill-outline-color": "#8faaa3",
              };
            if (layer.id === "places" && layer.type === "circle") {
              layer.filter = [
                "!",
                ["in", "_project_marker", ["to-string", ["get", "kind"]]],
              ];
              layer.paint = {
                ...layer.paint,
                "circle-color": "#839c97",
                "circle-radius": 3,
              };
            }
            map.addLayer(layer);
          }
          if (projectFeatures.length && projectExtent) {
            map.addSource("project", {
              type: "geojson",
              data: { type: "FeatureCollection", features: projectFeatures },
            });
            // One visual label for the programme, even when it has several buildings.
            // This derived label anchor is not stored as a project location.
            map.addSource("project-label", {
              type: "geojson",
              data: {
                type: "FeatureCollection",
                features: [
                  {
                    type: "Feature",
                    geometry: {
                      type: "Point",
                      coordinates: [
                        (projectExtent[0][0] + projectExtent[1][0]) / 2,
                        (projectExtent[0][1] + projectExtent[1][1]) / 2,
                      ],
                    },
                    properties: projectFeatures[0].properties,
                  },
                ],
              },
            });
            map.addLayer({
              id: "project-footprint",
              type: "fill",
              source: "project",
              filter: ["==", ["geometry-type"], "Polygon"],
              paint: { "fill-color": "#eb7939", "fill-opacity": 0.35 },
            });
            map.addLayer({
              id: "project-outline",
              type: "line",
              source: "project",
              filter: ["==", ["geometry-type"], "Polygon"],
              paint: { "line-color": "#eb7939", "line-width": 3 },
            });
            map.addLayer({
              id: "project-halo",
              type: "circle",
              source: "project",
              filter: ["==", ["geometry-type"], "Point"],
              paint: {
                "circle-radius": 22,
                "circle-color": "#eb7939",
                "circle-opacity": 0.22,
              },
            });
            map.addLayer({
              id: "project-point",
              type: "circle",
              source: "project",
              filter: ["==", ["geometry-type"], "Point"],
              paint: {
                "circle-radius": 9,
                "circle-color": "#eb7939",
                "circle-stroke-width": 3,
                "circle-stroke-color": "#fffefa",
              },
            });
            map.addLayer({
              id: "project-name",
              type: "symbol",
              source: "project-label",
              layout: {
                "text-field": mapName(locale),
                "text-font": ["Arial", "Noto Sans", "sans-serif"],
                "text-size": 15,
                "text-anchor": "top",
                "text-offset": [0, 1.5],
                "text-max-width": 20,
                "text-allow-overlap": true,
              },
              paint: {
                "text-color": "#123e46",
                "text-halo-color": "#fffefa",
                "text-halo-width": 3,
              },
            });
          }
        });
      })
      .catch(() => {
        if (!abort.signal.aborted) setFailed(true);
      });
    return () => {
      abort.abort();
      resize?.disconnect();
      map?.remove();
    };
  }, [bounds, territory, locations, locale, label, mapLabels]);
  return (
    <section className={styles.localMap} ref={root} aria-label={label}>
      {failed && (
        <p className={styles.mapError} role="status">
          {unavailable}
        </p>
      )}
    </section>
  );
}
