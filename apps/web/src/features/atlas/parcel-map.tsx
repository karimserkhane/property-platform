"use client";

import { brand } from "@property-platform/branding";
import {
  AttributionControl,
  type GeoJSONSource,
  Map as LibreMap,
  NavigationControl,
  ScaleControl,
  setWorkerUrl,
} from "maplibre-gl";
import { useEffect, useMemo, useRef } from "react";
import { mapControlLabels, mapLayers, mapName } from "./map-style";
import {
  buildingAtPoint,
  type Category,
  COLORS,
  districtBounds,
  download,
  geometryBounds,
  geometryClickArea,
  selectMapHit,
} from "./presentation";
import type {
  ImageryScene,
  MapContext,
  MapFeature,
  MapLabels,
  ParcelCollection,
  Territory,
} from "./types";
import "maplibre-gl/dist/maplibre-gl.css";

setWorkerUrl(
  new URL(
    "maplibre-gl/dist/maplibre-gl-worker.mjs",
    import.meta.url,
  ).toString(),
);
export type MapOptions = {
  streets: boolean;
  buildings: boolean;
  places: boolean;
  areas: boolean;
  names: boolean;
  codes: boolean;
  satellite: boolean;
  scene: string;
};
export type MapView = {
  kind: "area" | "focus" | "near" | "feature" | "export";
  token: number;
  feature?: Pick<MapFeature, "geometry">;
};

function boundsOf(bounds: number[]): [[number, number], [number, number]] {
  return [
    [bounds[0], bounds[1]],
    [bounds[2], bounds[3]],
  ];
}

export default function ParcelMap({
  data,
  context,
  selected,
  activeFeature,
  onSelect,
  onFeature,
  onError,
  label,
  options,
  view,
  locale,
  imagery,
  m,
  territory,
  countryBounds,
}: {
  data: ParcelCollection;
  context: MapContext | null;
  selected: string | null;
  activeFeature: MapFeature | null;
  onSelect: (id: string) => void;
  onFeature: (feature: MapFeature) => void;
  onError: () => void;
  label: string;
  options: MapOptions;
  view: MapView;
  locale: string;
  imagery: ImageryScene[];
  m: MapLabels;
  territory: Territory;
  countryBounds: number[];
}) {
  const element = useRef<HTMLElement>(null);
  // The parent keys the map by locale; native controls receive that mount's labels.
  const controlLabels = useRef(mapControlLabels(m, label));
  const map = useRef<LibreMap | null>(null);
  const consumedView = useRef(0);
  const initialFrame = useRef(false);
  const coordinates = useRef<HTMLOutputElement>(null);
  const callbacks = useRef({ onSelect, onFeature, onError });
  callbacks.current = { onSelect, onFeature, onError };
  const contextRef = useRef(context);
  contextRef.current = context;
  const optionsRef = useRef(options);
  optionsRef.current = options;
  const parcelAreas = useMemo(
    () =>
      new Map(data.features.map((f) => [f.id, geometryClickArea(f.geometry)])),
    [data],
  );
  const parcelAreasRef = useRef(parcelAreas);
  parcelAreasRef.current = parcelAreas;
  const credits = useMemo(
    () =>
      [
        ...new Set(
          [
            ...data.features.map((feature) => feature.properties.source_name),
            // Point research references are credited in their cards, rather than filling the base-map footer.
            ...[
              context?.street,
              context?.building,
              context?.administrative_area,
            ].flatMap((collection) =>
              (collection?.features ?? []).map(
                (feature) => feature.properties.source.name,
              ),
            ),
          ].filter((name): name is string => Boolean(name)),
        ),
      ].map((name) =>
        name.startsWith("OpenStreetMap")
          ? "© OpenStreetMap contributors · ODbL"
          : name,
      ),
    [data, context],
  );
  useEffect(() => {
    if (!element.current) return;
    consumedView.current = 0;
    let instance: LibreMap;
    try {
      instance = new LibreMap({
        container: element.current,
        locale: controlLabels.current,
        bounds: boundsOf(territory.camera_bounds),
        fitBoundsOptions: { padding: 30, animate: false },
        minZoom: 5,
        maxZoom: 20,
        maxBounds: boundsOf(countryBounds),
        canvasContextAttributes: { preserveDrawingBuffer: true },
        style: {
          version: 8,
          sources: {},
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": "#e9f0f2" },
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
    const resize = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0 && entry.contentRect.height > 0)
        instance.resize();
    });
    resize.observe(element.current);
    instance.addControl(
      new NavigationControl({ showCompass: true }),
      "top-right",
    );
    instance.addControl(new ScaleControl({ unit: "metric" }), "bottom-right");
    const lostContext = () => callbacks.current.onError();
    instance.getCanvas().addEventListener("webglcontextlost", lostContext);
    instance.on("mousemove", (event) => {
      if (coordinates.current)
        coordinates.current.textContent = `${event.lngLat.lng.toFixed(6)}, ${event.lngLat.lat.toFixed(6)}`;
    });
    instance.on("load", () => {
      for (const id of [
        "parcels",
        "street",
        "building",
        "place",
        "administrative_area",
      ])
        instance.addSource(id, {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
      instance.addSource("satellite", {
        type: "raster",
        tiles: [
          "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        attribution:
          "Esri, Maxar, Earthstar Geographics and the GIS User Community",
      });
      for (const layer of mapLayers("en")) instance.addLayer(layer);
      instance.on("click", (event) => {
        const hits = instance.queryRenderedFeatures(event.point, {
          layers: [
            "buildings",
            "places",
            "place-names",
            "streets",
            "street-names",
            "parcel-fill",
          ],
        });
        const hit = selectMapHit(hits, parcelAreasRef.current);
        const footprint =
          optionsRef.current.buildings &&
          buildingAtPoint(contextRef.current?.building.features ?? [], [
            event.lngLat.lng,
            event.lngLat.lat,
          ]);
        if (footprint && hit?.layer.id !== "buildings") {
          callbacks.current.onFeature(footprint);
          return;
        }
        if (!hit) return;
        const id = String(hit.properties.id);
        if (hit.layer.id === "parcel-fill") callbacks.current.onSelect(id);
        else {
          const target = ["places", "place-names"].includes(hit.layer.id)
            ? "place"
            : hit.layer.id === "buildings"
              ? "building"
              : "street";
          const feature = contextRef.current?.[target].features.find(
            (f) => f.properties.id === id,
          );
          if (feature) callbacks.current.onFeature(feature);
        }
      });
    });
    return () => {
      resize.disconnect();
      map.current = null;
      instance.getCanvas().removeEventListener("webglcontextlost", lostContext);
      instance.remove();
    };
  }, [countryBounds, territory.camera_bounds]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const control = new AttributionControl({
      // Use MapLibre's responsive attribution control on narrow maps.
      // Layer names stay in the source details and PNG export. Attribute the
      // common provider once here so island/layer repeats do not cover the map.
      customAttribution: [
        ...new Set(
          credits.map((credit) =>
            credit.startsWith("DMT / Onwani") ? "DMT / Onwani" : credit,
          ),
        ),
      ].map((credit) =>
        credit === "© OpenStreetMap contributors · ODbL"
          ? '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors · ODbL</a>'
          : credit.replace(
              /[&<>"']/g,
              (character) =>
                ({
                  "&": "&amp;",
                  "<": "&lt;",
                  ">": "&gt;",
                  '"': "&quot;",
                  "'": "&#39;",
                })[character] ?? character,
            ),
      ),
    });
    instance.addControl(control);
    return () => {
      // Map.remove() already disposes controls when the territory unmounts.
      if (map.current === instance) instance.removeControl(control);
    };
  }, [credits]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const update = () => {
      for (const id of ["street-names", "place-names", "area-names"]) {
        if (instance.getLayer(id))
          instance.setLayoutProperty(id, "text-field", mapName(locale));
      }
    };
    // isStyleLoaded() also becomes false during source work after initial load.
    // Our sentinel source marks initialisation; a second "load" event will not follow.
    if (instance.getSource("parcels")) update();
    else instance.once("load", update);
    return () => {
      instance.off("load", update);
    };
  }, [locale]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const update = () => {
      for (const [id, collection] of [
        ["parcels", data],
        ...Object.entries(context ?? {}),
      ] as const) {
        const source = instance.getSource(id) as GeoJSONSource | undefined;
        source?.setData(
          collection as unknown as Parameters<GeoJSONSource["setData"]>[0],
        );
      }
      if (!consumedView.current && !initialFrame.current) {
        const bounds = districtBounds(
          context?.administrative_area.features ?? [],
        );
        if (bounds) {
          instance.fitBounds(bounds, { padding: 30, duration: 0 });
          initialFrame.current = true;
        }
      }
    };
    if (instance.getSource("parcels")) update();
    else instance.once("load", update);
    return () => {
      instance.off("load", update);
    };
  }, [data, context]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const update = () => {
      if (instance.getLayer("selection"))
        instance.setFilter("selection", ["==", ["get", "id"], selected ?? ""]);
      for (const [id, type] of [
        ["building-selection", "MultiPolygon"],
        ["place-selection", "Point"],
        ["street-selection", "MultiLineString"],
      ] as const) {
        if (instance.getLayer(id))
          instance.setFilter(id, [
            "==",
            ["get", "id"],
            activeFeature?.geometry.type === type ? activeFeature.id : "",
          ]);
      }
    };
    if (instance.getSource("parcels")) update();
    else instance.once("load", update);
    return () => {
      instance.off("load", update);
    };
  }, [selected, activeFeature]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const update = () => {
      for (const scene of imagery) {
        if (!instance.getSource(scene.id)) {
          instance.addSource(scene.id, {
            type: "image",
            url: scene.image_url,
            coordinates: scene.coordinates as [
              [number, number],
              [number, number],
              [number, number],
              [number, number],
            ],
          });
          instance.addLayer(
            {
              id: scene.id,
              type: "raster",
              source: scene.id,
              layout: { visibility: "none" },
            },
            "land",
          );
        }
        instance.setLayoutProperty(
          scene.id,
          "visibility",
          options.satellite && options.scene === scene.id ? "visible" : "none",
        );
      }
      const visibility: Record<string, boolean> = {
        streets: options.streets,
        "street-casing": options.streets,
        "street-names": options.streets && options.names,
        buildings: options.buildings,
        "building-selection": options.buildings,
        places: options.places,
        "place-selection": options.places,
        "street-selection": options.streets,
        "place-names": options.places && options.names,
        "parcel-codes": options.codes,
        areas: options.areas,
        "area-names": options.areas && options.names,
        satellite: options.satellite && options.scene === "esri",
        land: !options.satellite,
      };
      for (const [id, show] of Object.entries(visibility))
        if (instance.getLayer(id))
          instance.setLayoutProperty(
            id,
            "visibility",
            show ? "visible" : "none",
          );
      if (instance.getLayer("parcel-fill"))
        instance.setPaintProperty(
          "parcel-fill",
          "fill-opacity",
          options.satellite
            ? 0.22
            : ["case", ["==", ["get", "category"], "overlay"], 0.15, 0.86],
        );
    };
    if (instance.getSource("parcels")) update();
    else instance.once("load", update);
    return () => {
      instance.off("load", update);
    };
  }, [options, imagery]);

  useEffect(() => {
    const instance = map.current;
    if (!instance || !view.token || consumedView.current === view.token) return;
    instance.resize();
    consumedView.current = view.token;
    if (view.kind === "export") {
      // GeoJSON workers and local glyphs can still be preparing the current view.
      // A render event alone can precede those results and produce a partial export.
      const event = instance.loaded() ? "render" : "idle";
      const exportImage = () => {
        const source = instance.getCanvas();
        const canvas = document.createElement("canvas");
        canvas.width = source.width;
        canvas.height = source.height + 150;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.drawImage(source, 0, 0);
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, source.height, canvas.width, 150);
        ctx.fillStyle = "#123c40";
        ctx.font = "18px sans-serif";
        ctx.fillText(
          `${brand.displayName} · ${locale === "ar" ? territory.name_ar : territory.name} · ${options.satellite ? options.scene : m.plan}`,
          16,
          source.height + 25,
        );
        ctx.font = "14px sans-serif";
        Object.entries(COLORS).forEach(([key, color], i) => {
          const x = 16 + ((i % 4) * canvas.width) / 4,
            y = source.height + 48 + Math.floor(i / 4) * 26;
          ctx.fillStyle = color;
          ctx.fillRect(x, y, 13, 13);
          ctx.fillStyle = "#123c40";
          ctx.fillText(
            m[key as Category],
            x + 19,
            y + 12,
            canvas.width / 4 - 35,
          );
        });
        ctx.font = "12px sans-serif";
        ctx.fillText(credits.join(" · "), 16, source.height + 116);
        if (options.satellite)
          ctx.fillText(
            options.scene === "esri"
              ? "Esri, Maxar, Earthstar Geographics and the GIS User Community"
              : "Contains modified Copernicus Sentinel data (2026) · Earth Search",
            16,
            source.height + 137,
          );
        canvas.toBlob((blob) => {
          if (blob) download(blob, `${territory.id}-map.png`);
        });
      };
      instance.once(event, exportImage);
      instance.triggerRepaint();
      return () => {
        instance.off(event, exportImage);
      };
    } else if (view.kind === "focus" && territory.focus_bounds)
      instance.fitBounds(boundsOf(territory.focus_bounds), {
        padding: 40,
        duration: 0,
      });
    else if (view.kind === "near" && territory.neighbourhood_bounds)
      instance.fitBounds(boundsOf(territory.neighbourhood_bounds), {
        padding: 40,
        duration: 0,
      });
    else if (view.kind === "feature" && view.feature) {
      if (view.feature.geometry.type === "Point")
        instance.easeTo({
          center: view.feature.geometry.coordinates as [number, number],
          zoom: 16.5,
          duration: 0,
        });
      else {
        const bounds = geometryBounds(view.feature.geometry);
        if (bounds)
          instance.fitBounds(bounds, { padding: 60, maxZoom: 17, duration: 0 });
      }
    } else {
      const bounds = districtBounds(
        contextRef.current?.administrative_area.features ?? [],
      );
      instance.fitBounds(bounds ?? boundsOf(territory.camera_bounds), {
        padding: 30,
        duration: 0,
      });
    }
  }, [view, m, options.satellite, options.scene, locale, territory, credits]);
  return (
    <>
      <section ref={element} className="parcel-map" aria-label={label} />
      <output
        ref={coordinates}
        className="map-coordinates"
        aria-label={m.coordinates}
      />
    </>
  );
}
