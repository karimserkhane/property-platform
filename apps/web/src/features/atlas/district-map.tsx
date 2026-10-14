"use client";

import type { components } from "@property-platform/contracts";
import {
  type GeoJSONSource,
  Map as LibreMap,
  NavigationControl,
  setWorkerUrl,
} from "maplibre-gl";
import { useEffect, useRef } from "react";
import "maplibre-gl/dist/maplibre-gl.css";

export type DistrictMapData = components["schemas"]["DistrictMapResponse"];
export type DistrictFeature = DistrictMapData["features"][number];
export type DistrictView = { token: number; districtId: string | null };
setWorkerUrl(
  new URL(
    "maplibre-gl/dist/maplibre-gl-worker.mjs",
    import.meta.url,
  ).toString(),
);

export default function DistrictMap({
  data,
  locale,
  selected,
  onSelect,
  onError,
  label,
  view,
}: {
  data: DistrictMapData;
  locale: string;
  selected: string | null;
  onSelect: (id: string) => void;
  onError: () => void;
  label: string;
  view: DistrictView;
}) {
  const container = useRef<HTMLElement>(null);
  const map = useRef<LibreMap | null>(null);
  const callbacks = useRef({ onSelect, onError });
  callbacks.current = { onSelect, onError };
  useEffect(() => {
    if (!container.current || !data.features.length) return;
    const extent = data.features.reduce(
      (box, f) => [
        Math.min(box[0], f.properties.bounds[0]),
        Math.min(box[1], f.properties.bounds[1]),
        Math.max(box[2], f.properties.bounds[2]),
        Math.max(box[3], f.properties.bounds[3]),
      ],
      [Infinity, Infinity, -Infinity, -Infinity],
    );
    let instance: LibreMap;
    try {
      instance = new LibreMap({
        container: container.current,
        bounds: [
          [extent[0], extent[1]],
          [extent[2], extent[3]],
        ],
        fitBoundsOptions: { padding: 30, animate: false },
        minZoom: 5,
        maxZoom: 18,
        style: {
          version: 8,
          sources: {},
          layers: [
            {
              id: "water",
              type: "background",
              paint: { "background-color": "#dce9ed" },
            },
          ],
        },
        attributionControl: false,
      });
    } catch {
      callbacks.current.onError();
      return;
    }
    map.current = instance;
    instance.addControl(new NavigationControl(), "top-right");
    const contextLost = () => callbacks.current.onError();
    instance.getCanvas().addEventListener("webglcontextlost", contextLost);
    instance.on("load", () => {
      instance.addSource("districts", {
        type: "geojson",
        data: data as unknown as Parameters<GeoJSONSource["setData"]>[0],
      });
      instance.addSource("labels", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: data.features.map((f) => ({
            type: "Feature",
            geometry: { type: "Point", coordinates: f.properties.label_point },
            properties: { ...f.properties, id: f.id },
          })),
        },
      });
      instance.addLayer({
        id: "district-fill",
        type: "fill",
        source: "districts",
        paint: {
          "fill-color": [
            "match",
            ["get", "municipality"],
            "ADM",
            "#d7dfce",
            "AAM",
            "#e3d5b8",
            "#d8d0c5",
          ],
          "fill-opacity": 0.8,
        },
      });
      instance.addLayer({
        id: "district-lines",
        type: "line",
        source: "districts",
        paint: { "line-color": "#728a80", "line-width": 1 },
      });
      instance.addLayer({
        id: "selected-district",
        type: "line",
        source: "districts",
        filter: ["==", ["get", "source_record_id"], ""],
        paint: { "line-color": "#c47d46", "line-width": 3 },
      });
      instance.addLayer({
        id: "district-labels",
        type: "symbol",
        source: "labels",
        layout: {
          "text-field": [
            "case",
            ["all", ["==", locale, "ar"], ["!=", ["get", "name_ar"], ""]],
            ["get", "name_ar"],
            ["get", "name"],
          ],
          "text-font": ["Arial", "Noto Sans", "sans-serif"],
          "text-size": 12,
          "text-max-width": 13,
        },
        paint: {
          "text-color": "#204d4f",
          "text-halo-color": "#fff",
          "text-halo-width": 2,
        },
      });
      instance.on("click", (event) => {
        const hits = instance.queryRenderedFeatures(event.point, {
          layers: ["district-labels", "district-fill"],
        });
        const id = hits[0]?.properties?.source_record_id;
        if (id) callbacks.current.onSelect(String(id));
      });
    });
    return () => {
      map.current = null;
      instance.getCanvas().removeEventListener("webglcontextlost", contextLost);
      instance.remove();
    };
  }, [data, locale]);
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const update = () =>
      instance.setFilter("selected-district", [
        "==",
        ["get", "source_record_id"],
        selected ?? "",
      ]);
    if (instance.getLayer("selected-district")) update();
    else instance.once("load", update);
    return () => {
      instance.off("load", update);
    };
  }, [selected]);
  useEffect(() => {
    const instance = map.current;
    if (!instance || !view.token) return;
    const update = () => {
      const chosen = data.features.find((f) => f.id === view.districtId);
      const bounds =
        chosen?.properties.bounds ??
        data.features.reduce(
          (box, f) => [
            Math.min(box[0], f.properties.bounds[0]),
            Math.min(box[1], f.properties.bounds[1]),
            Math.max(box[2], f.properties.bounds[2]),
            Math.max(box[3], f.properties.bounds[3]),
          ],
          [Infinity, Infinity, -Infinity, -Infinity],
        );
      instance.fitBounds(
        [
          [bounds[0], bounds[1]],
          [bounds[2], bounds[3]],
        ],
        { padding: 30, duration: 0 },
      );
    };
    if (instance.getSource("districts")) update();
    else instance.once("load", update);
    return () => {
      instance.off("load", update);
    };
  }, [data, view]);
  return (
    <section
      ref={container}
      className="district-overview-map"
      aria-label={label}
    />
  );
}
