"use client";

import { Map as LibreMap, NavigationControl, setWorkerUrl } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { mapControlLabels, mapLayers } from "../atlas/map-style";
import type { MapContext, MapLabels } from "../atlas/types";
import styles from "./project.module.css";
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
  slug,
  locale,
  label,
  mapLabels,
  unavailable,
}: {
  territory: string;
  bounds: number[];
  slug: string;
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
    const search = new URLSearchParams({ territory, bbox: bounds.join(",") });
    void fetch(`/api/atlas/map-context?${search}`, {
      signal: AbortSignal.any([abort.signal, AbortSignal.timeout(10000)]),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("unavailable");
        return (await response.json()) as MapContext;
      })
      .then((data) => {
        if (abort.signal.aborted || !root.current) return;
        map = new LibreMap({
          container: root.current,
          bounds: extent,
          maxBounds: extent,
          fitBoundsOptions: { padding: 24, animate: false },
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
          ))
            map.addLayer(layer);
          // A pin is shown only for a stored point explicitly linked to this project.
          const points = data.place.features.filter(
            (feature) =>
              feature.geometry.type === "Point" &&
              feature.properties.presentation?.project?.slug === slug,
          );
          if (points.length) {
            map.addSource("project", {
              type: "geojson",
              data: { type: "FeatureCollection", features: points },
            });
            map.addLayer({
              id: "project-halo",
              type: "circle",
              source: "project",
              paint: {
                "circle-radius": 15,
                "circle-color": "#b98e52",
                "circle-opacity": 0.22,
              },
            });
            map.addLayer({
              id: "project-point",
              type: "circle",
              source: "project",
              paint: {
                "circle-radius": 7,
                "circle-color": "#b98e52",
                "circle-stroke-width": 3,
                "circle-stroke-color": "#fffefa",
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
  }, [bounds, territory, slug, locale, label, mapLabels]);
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
