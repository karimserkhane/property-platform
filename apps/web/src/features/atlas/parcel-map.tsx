"use client";

import { type GeoJSONSource, Map as LibreMap, setWorkerUrl } from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { ParcelCollection } from "./types";
import "maplibre-gl/dist/maplibre-gl.css";

setWorkerUrl(
  new URL(
    "maplibre-gl/dist/maplibre-gl-worker.mjs",
    import.meta.url,
  ).toString(),
);

export default function ParcelMap({
  data,
  selected,
  onSelect,
  onError,
  label,
}: {
  data: ParcelCollection;
  selected: string | null;
  onSelect: (id: string) => void;
  onError: () => void;
  label: string;
}) {
  const element = useRef<HTMLDivElement>(null);
  const map = useRef<LibreMap | null>(null);
  const callbacks = useRef({ onSelect, onError });
  callbacks.current = { onSelect, onError };
  useEffect(() => {
    if (!element.current) return;
    let instance: LibreMap;
    try {
      instance = new LibreMap({
        container: element.current,
        center: [54.416, 24.498],
        zoom: 13.1,
        bounds: [
          [54.385, 24.465],
          [54.445, 24.53],
        ],
        fitBoundsOptions: { padding: 24, animate: false },
        minZoom: 11,
        maxZoom: 19,
        maxBounds: [
          [54.36, 24.44],
          [54.47, 24.55],
        ],
        style: {
          version: 8,
          sources: {},
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": "#dcebed" },
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
    instance.on("error", () => callbacks.current.onError());
    instance.on("load", () => {
      instance.addSource("parcels", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      instance.addLayer({
        id: "parcel-fill",
        type: "fill",
        source: "parcels",
        paint: { "fill-color": "#e7e3d7", "fill-opacity": 0.95 },
      });
      instance.addLayer({
        id: "parcel-line",
        type: "line",
        source: "parcels",
        paint: { "line-color": "#5b7a79", "line-width": 0.8 },
      });
      instance.addLayer({
        id: "selection",
        type: "line",
        source: "parcels",
        filter: ["==", ["get", "id"], ""],
        paint: { "line-color": "#075e63", "line-width": 4 },
      });
      instance.on("click", "parcel-fill", (event) => {
        const id = event.features?.[0]?.properties?.id;
        if (typeof id === "string") callbacks.current.onSelect(id);
      });
      instance.on("mouseenter", "parcel-fill", () => {
        instance.getCanvas().style.cursor = "pointer";
      });
      instance.on("mouseleave", "parcel-fill", () => {
        instance.getCanvas().style.cursor = "";
      });
    });
    return () => {
      map.current = null;
      instance.remove();
    };
  }, []);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const update = () => {
      const source = instance.getSource("parcels") as GeoJSONSource | undefined;
      source?.setData(
        data as unknown as Parameters<GeoJSONSource["setData"]>[0],
      );
      if (instance.getLayer("selection"))
        instance.setFilter("selection", ["==", ["get", "id"], selected ?? ""]);
    };
    if (instance.isStyleLoaded()) update();
    else instance.once("load", update);
    return () => {
      instance.off("load", update);
    };
  }, [data, selected]);

  return (
    <div ref={element} className="parcel-map" role="img" aria-label={label} />
  );
}
