"use client";

import { brand } from "@property-platform/branding";
import {
  AttributionControl,
  type GeoJSONSource,
  Map as LibreMap,
  NavigationControl,
  type Popup,
  ScaleControl,
  setWorkerUrl,
} from "maplibre-gl";
import { useTranslations } from "next-intl";
import { type RefObject, useEffect, useMemo, useRef, useState } from "react";
import {
  HYDROGRAPHY_CREDIT,
  HYDROGRAPHY_SOURCE,
  PLAN_COLORS,
} from "./hydrography";
import { BASEMAP_IMAGERY, imageryVisibility } from "./imagery-sources";
import { mapPlaceFilter, registerMapMarkers } from "./map-markers";
import { mapControlLabels, mapLayers, mapName } from "./map-style";
import {
  buildingAtPoint,
  type Category,
  COLORS,
  districtBounds,
  download,
  geometryBounds,
  parcelFillOpacity,
  parcelMapLabels,
  parcelPropertyIndex,
  selectMapHit,
} from "./presentation";
import { projectPulseFrame } from "./project-pulse";
import type {
  MapContext,
  MapFeature,
  MapLabels,
  ParcelIndex,
  Territory,
} from "./types";
import "maplibre-gl/dist/maplibre-gl.css";
import { registerArchivedTiles } from "./archived-tiles";
import {
  applyBuildingView,
  type BuildingView,
  setBuildingCamera,
} from "./building-3d";
import { showWorldBuilding } from "./building-popup";
import { boundsGeometry, mapToolActive } from "./map-analysis";
import { MapWorkbench } from "./map-workbench";
import {
  PARCEL_LABEL_SOURCE,
  PARCEL_SOURCE,
  parcelLabelPoints,
  parcelTileSource,
  syncParcelStates,
  tiledParcelLayers,
  tiledParcelOpacity,
} from "./parcel-tiles";
import { PROJECT_CLUSTER_LAYERS, zoomProjectCluster } from "./project-clusters";

setWorkerUrl(
  new URL(
    "maplibre-gl/dist/maplibre-gl-worker.mjs",
    import.meta.url,
  ).toString(),
);
export type MapOptions = BuildingView & {
  parcels: boolean;
  streets: boolean;
  buildings: boolean;
  places: boolean;
  commerce: boolean;
  offshore: boolean;
  areas: boolean;
  names: boolean;
  codes: boolean;
  pulse: boolean;
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
  selectionPanel,
  selectionVisible,
  onSelect,
  onFeature,
  onError,
  onContext,
  label,
  options,
  view,
  locale,
  m,
  territory,
  countryBounds,
}: {
  data: ParcelIndex;
  context: MapContext | null;
  selected: string | null;
  activeFeature: MapFeature | null;
  selectionPanel: RefObject<HTMLElement | null>;
  selectionVisible: boolean;
  onSelect: (id: string) => void;
  onFeature: (feature: MapFeature) => void;
  onError: () => void;
  onContext: () => void;
  label: string;
  options: MapOptions;
  view: MapView;
  locale: string;
  m: MapLabels;
  territory: Territory;
  countryBounds: number[];
}) {
  const usage = useTranslations("Use");
  const labelledParcels = useMemo(
    () =>
      parcelMapLabels(data, parcelPropertyIndex(context, data), locale, usage),
    [data, context, locale, usage],
  );
  const element = useRef<HTMLElement>(null);
  // The parent keys the map by locale; native controls receive that mount's labels.
  const controlLabels = useRef(mapControlLabels(m, label));
  const map = useRef<LibreMap | null>(null);
  const [toolMap, setToolMap] = useState<LibreMap | null>(null);
  const consumedView = useRef(0);
  const initialFrame = useRef(false);
  const coordinates = useRef<HTMLOutputElement>(null);
  const [imageryFailed, setImageryFailed] = useState(false);
  const [buildingsFailed, setBuildingsFailed] = useState(false);
  const worldPopup = useRef<Popup | null>(null);
  const popupLabels = useRef({ m, locale });
  popupLabels.current = { m, locale };
  const callbacks = useRef({ onSelect, onFeature, onError, onContext });
  callbacks.current = { onSelect, onFeature, onError, onContext };
  const contextRef = useRef(context);
  contextRef.current = context;
  const optionsRef = useRef(options);
  optionsRef.current = options;
  const activeRef = useRef(activeFeature);
  activeRef.current = activeFeature;
  const parcelAreas = useMemo(
    () => new Map(data.features.map((f) => [f.id, f.properties.area_m2])),
    [data],
  );
  const parcelAreasRef = useRef(parcelAreas);
  parcelAreasRef.current = parcelAreas;
  const parcelCategories = useMemo(
    () => new Map(data.features.map((f) => [f.id, f.properties.category])),
    [data],
  );
  const parcelCategoriesRef = useRef(parcelCategories);
  parcelCategoriesRef.current = parcelCategories;
  // Parcels currently listed by the index; tile features outside it stay hidden.
  const shownParcels = useRef<Set<string>>(new Set());
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
            ...(context?.place.features ?? [])
              .filter((feature) =>
                feature.properties.source.name.startsWith("Overture Maps"),
              )
              .map((feature) => feature.properties.source.name),
          ].filter((name): name is string => Boolean(name)),
        ),
      ].map((name) =>
        name.startsWith("OpenStreetMap")
          ? "© OpenStreetMap contributors · ODbL"
          : name.startsWith("Overture Maps")
            ? "Overture Maps · upstream contributors · CDLA / Apache / CC0"
            : name,
      ),
    [data, context],
  );
  useEffect(() => {
    if (!element.current) return;
    consumedView.current = 0;
    let instance: LibreMap;
    try {
      registerArchivedTiles();
      instance = new LibreMap({
        container: element.current,
        locale: controlLabels.current,
        bounds: boundsOf(territory.camera_bounds),
        fitBoundsOptions: { padding: 30, animate: false },
        minZoom: 5,
        maxZoom: 20,
        maxPitch: 70,
        maxBounds: boundsOf(countryBounds),
        canvasContextAttributes: { preserveDrawingBuffer: true },
        style: {
          version: 8,
          sources: {},
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": PLAN_COLORS.land },
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
    instance.on("error", (event) => {
      if (
        "sourceId" in event &&
        event.sourceId === "hydrography" &&
        optionsRef.current.dimension === "3d"
      )
        setBuildingsFailed(true);
      const active = BASEMAP_IMAGERY.find(
        (item) => item.id === optionsRef.current.scene,
      );
      if (
        optionsRef.current.satellite &&
        "sourceId" in event &&
        event.sourceId === active?.layerId
      )
        setImageryFailed(true);
    });
    const resize = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0 && entry.contentRect.height > 0)
        instance.resize();
    });
    resize.observe(element.current);
    instance.addControl(
      new NavigationControl({ showCompass: true, visualizePitch: true }),
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
      instance.addSource("hydrography", HYDROGRAPHY_SOURCE);
      instance.addSource(
        PARCEL_SOURCE,
        parcelTileSource(window.location.origin, territory.id),
      );
      for (const id of [
        PARCEL_LABEL_SOURCE,
        "street",
        "building",
        "place",
        "administrative_area",
      ])
        instance.addSource(id, {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
      for (const provider of BASEMAP_IMAGERY)
        instance.addSource(provider.layerId, {
          type: "raster",
          tiles: [provider.tiles],
          tileSize: 256,
          minzoom: provider.minzoom,
          maxzoom: provider.maxzoom,
          attribution: provider.attribution,
        });
      registerMapMarkers(instance);
      for (const layer of tiledParcelLayers(mapLayers("en")))
        instance.addLayer(layer);
      setToolMap(instance);
      instance.on("click", (event) => {
        if (mapToolActive(instance) || zoomProjectCluster(instance, event))
          return;
        const hits = instance.queryRenderedFeatures(event.point, {
          layers: [
            ...PROJECT_CLUSTER_LAYERS.filter(
              (id) => id !== "cluster-projects" && instance.getLayer(id),
            ),
            "buildings",
            "buildings-3d",
            "places",
            "place-names",
            "project-names",
            "streets",
            "street-names",
            "parcel-fill",
            "parcel-project-names",
            "parcel-use-names",
            ...(optionsRef.current.areas
              ? ["area-hit", "area-names", "areas"]
              : []),
          ],
        });
        {
          const { x, y } = event.point;
          hits.unshift(
            ...instance
              .queryRenderedFeatures(
                [
                  [x - 8, y - 8],
                  [x + 8, y + 8],
                ],
                {
                  layers: [
                    "places",
                    "project-names",
                    ...PROJECT_CLUSTER_LAYERS.filter(
                      (id) =>
                        id !== "cluster-projects" && instance.getLayer(id),
                    ),
                  ],
                },
              )
              .filter((f) =>
                String(f.properties.kind).endsWith("_project_marker"),
              ),
          );
        }
        const overWater =
          !optionsRef.current.satellite &&
          !optionsRef.current.offshore &&
          instance.queryRenderedFeatures(event.point, {
            layers: ["plan-water"],
          }).length > 0;
        const listed = hits.filter(
          (item) =>
            item.source !== PARCEL_SOURCE ||
            shownParcels.current.has(String(item.properties.id)),
        );
        // Plots drawn over mapped water stay selectable; project perimeters
        // (not drawn there) do not capture a click on the open water.
        const hit = selectMapHit(
          overWater
            ? listed.filter(
                (item) =>
                  (item.source !== PARCEL_SOURCE &&
                    item.source !== PARCEL_LABEL_SOURCE) ||
                  parcelCategoriesRef.current.get(
                    String(item.properties.id),
                  ) !== "overlay",
              )
            : listed,
          parcelAreasRef.current,
        );
        const footprint =
          optionsRef.current.buildings &&
          buildingAtPoint(contextRef.current?.building.features ?? [], [
            event.lngLat.lng,
            event.lngLat.lat,
          ]);
        const projectHit = String(hit?.properties.kind).endsWith(
          "_project_marker",
        );
        worldPopup.current?.remove();
        if (
          !projectHit &&
          optionsRef.current.dimension === "3d" &&
          optionsRef.current.buildings &&
          optionsRef.current.buildingSource === "openstreetmap"
        ) {
          const worldHit = instance.queryRenderedFeatures(event.point, {
            layers: ["world-buildings-3d"],
          })[0];
          if (worldHit) {
            callbacks.current.onContext();
            worldPopup.current = showWorldBuilding(
              instance,
              event.lngLat,
              worldHit,
              popupLabels.current.m,
              popupLabels.current.locale,
            );
            return;
          }
        }
        if (
          footprint &&
          hit?.layer.id !== "buildings" &&
          hit?.layer.id !== "buildings-3d" &&
          !projectHit
        ) {
          callbacks.current.onFeature(footprint);
          return;
        }
        if (!hit) return;
        const id = String(hit.properties.id);
        if (
          ["parcel-fill", "parcel-project-names", "parcel-use-names"].includes(
            hit.layer.id,
          )
        )
          callbacks.current.onSelect(id);
        else {
          const target = [
            "places",
            "place-names",
            "project-names",
            "single-project",
            "close-project",
          ].includes(hit.layer.id)
            ? "place"
            : ["buildings", "buildings-3d"].includes(hit.layer.id)
              ? "building"
              : ["area-hit", "areas", "area-names"].includes(hit.layer.id)
                ? "administrative_area"
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
      worldPopup.current?.remove();
      map.current = null;
      setToolMap(null);
      instance.getCanvas().removeEventListener("webglcontextlost", lostContext);
      instance.remove();
    };
  }, [countryBounds, territory.camera_bounds, territory.id]);

  // Keep the selected object above the phone sheet without changing the zoom.
  // biome-ignore lint/correctness/useExhaustiveDependencies: a locate command must recheck phone-sheet occlusion after moving the camera.
  useEffect(() => {
    const instance = map.current;
    const panel = selectionPanel.current;
    if (!instance || !panel || !selectionVisible) return;
    let frame = 0;
    const reveal = () => {
      const root = element.current;
      const row = data.features.find((item) => item.id === selected);
      const geometry =
        activeFeature?.geometry ??
        (row ? boundsGeometry(row.properties.bounds) : undefined);
      if (
        !root ||
        root.clientWidth > 760 ||
        !geometry ||
        !panel.getClientRects().length
      )
        return;
      const bounds = geometryBounds(geometry);
      if (!bounds) return;
      const point = instance.project([
        (bounds[0][0] + bounds[1][0]) / 2,
        (bounds[0][1] + bounds[1][1]) / 2,
      ]);
      const mapRect = root.getBoundingClientRect();
      const cardRect = panel.getBoundingClientRect();
      const x = point.x + mapRect.left,
        y = point.y + mapRect.top;
      if (
        x >= cardRect.left &&
        x <= cardRect.right &&
        y >= cardRect.top &&
        y <= cardRect.bottom
      ) {
        const clearHeight = Math.max(0, cardRect.top - mapRect.top - 16);
        instance.panBy([0, point.y - Math.max(32, clearHeight * 0.65)], {
          duration: 0,
        });
      }
    };
    const schedule = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(reveal);
    };
    const observer = new ResizeObserver(schedule);
    observer.observe(panel);
    instance.on("load", schedule);
    schedule();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      instance.off("load", schedule);
    };
  }, [
    activeFeature,
    selected,
    data,
    selectionPanel,
    selectionVisible,
    view.token,
  ]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0,
      last = -Infinity;
    const paint = (radius: number, opacity: number) => {
      if (!instance.getLayer("project-halo")) return;
      instance.setPaintProperty("project-halo", "circle-radius", radius);
      instance.setPaintProperty("project-halo", "circle-opacity", opacity);
    };
    const animate = (time: number) => {
      if (time - last >= 60) {
        const value = projectPulseFrame(time);
        paint(value.radius, value.opacity);
        last = time;
      }
      frame = requestAnimationFrame(animate);
    };
    const refresh = () => {
      cancelAnimationFrame(frame);
      paint(13, 0.16);
      if (options.pulse && !document.hidden && !reduced.matches)
        frame = requestAnimationFrame(animate);
    };
    if (instance.getSource("parcels")) refresh();
    else instance.on("load", refresh);
    document.addEventListener("visibilitychange", refresh);
    reduced.addEventListener("change", refresh);
    return () => {
      cancelAnimationFrame(frame);
      instance.off("load", refresh);
      document.removeEventListener("visibilitychange", refresh);
      reduced.removeEventListener("change", refresh);
    };
  }, [options.pulse]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const control = new AttributionControl({
      compact: true,
      // Keep credits accessible without covering the mobile map by default.
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
    // Raster providers can expand the credit rail on narrow maps. Keep our
    // corner controls above the rendered credits, including when they collapse.
    const rail = instance
      .getContainer()
      .querySelector<HTMLElement>(".maplibregl-ctrl-bottom-right");
    const shell = element.current?.closest<HTMLElement>(".atlas-shell");
    const measureFooter = () =>
      shell?.style.setProperty(
        "--map-footer-height",
        `${Math.ceil(rail?.getBoundingClientRect().height ?? 0)}px`,
      );
    const footerObserver = new ResizeObserver(measureFooter);
    if (rail) footerObserver.observe(rail);
    measureFooter();
    return () => {
      footerObserver.disconnect();
      // Map.remove() already disposes controls when the territory unmounts.
      if (map.current === instance) instance.removeControl(control);
    };
  }, [credits]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const update = () => {
      for (const id of [
        "street-names",
        "place-names",
        "project-names",
        "area-names",
      ]) {
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
      shownParcels.current = syncParcelStates(
        instance,
        labelledParcels,
        shownParcels.current,
      );
      for (const [id, collection] of [
        [PARCEL_LABEL_SOURCE, parcelLabelPoints(labelledParcels)],
        ...Object.entries(context ?? {}),
      ] as const) {
        const source = instance.getSource(id) as GeoJSONSource | undefined;
        source?.setData(
          collection as unknown as Parameters<GeoJSONSource["setData"]>[0],
        );
      }
      if (
        !consumedView.current &&
        !initialFrame.current &&
        optionsRef.current.dimension !== "3d"
      ) {
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
  }, [labelledParcels, context]);

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
        ["area-selection", "MultiPolygon"],
      ] as const) {
        if (instance.getLayer(id))
          instance.setFilter(id, [
            "==",
            ["get", "id"],
            activeFeature?.geometry.type === type ? activeFeature.id : "",
          ]);
      }
      applyBuildingView(
        instance,
        optionsRef.current,
        optionsRef.current.buildings,
        activeFeature?.geometry.type === "MultiPolygon"
          ? activeFeature.id
          : null,
      );
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
      setImageryFailed(false);
      setBuildingsFailed(false);
      worldPopup.current?.remove();
      const provider = BASEMAP_IMAGERY.find(
        (item) => item.id === options.scene,
      );
      instance.setMinZoom(
        options.satellite ? Math.max(5, provider?.minzoom ?? 5) : 5,
      );
      const visibility: Record<string, boolean> = {
        "parcel-fill": options.parcels,
        "parcel-line": options.parcels,
        // Faint plots over mapped water: plan only, and redundant once solid
        // outlines are raised above the water by the expert toggle.
        "parcel-water-fill": options.parcels && !options.satellite,
        "parcel-water-line":
          options.parcels && !options.satellite && !options.offshore,
        ...imageryVisibility(options.satellite, options.scene),
        "plan-water": !options.satellite,
        "plan-waterways": !options.satellite,
        streets: options.streets,
        "street-casing": options.streets,
        "street-names": options.streets && options.names,
        buildings: options.buildings,
        "building-selection": options.buildings,
        places: options.places || options.commerce,
        "project-halo": true,
        "place-selection": options.places || options.commerce,
        "street-selection": options.streets,
        "place-names": (options.places || options.commerce) && options.names,
        "project-names": options.names,
        "parcel-codes": options.parcels && options.codes,
        "parcel-project-names": false,
        "parcel-use-names": false,
        areas: options.areas,
        "area-hit": options.areas,
        "area-selection": options.areas,
        "area-names": options.areas && options.names,
        land: !options.satellite,
      };
      for (const [id, show] of Object.entries(visibility))
        if (instance.getLayer(id))
          instance.setLayoutProperty(
            id,
            "visibility",
            show ? "visible" : "none",
          );
      for (const id of ["places", "place-names"])
        instance.setFilter(
          id,
          mapPlaceFilter(options.commerce, options.places),
        );
      instance.moveLayer(
        "parcel-line",
        options.offshore || options.satellite ? "buildings" : "plan-water",
      );
      if (instance.getLayer("parcel-fill"))
        instance.setPaintProperty(
          "parcel-fill",
          "fill-opacity",
          tiledParcelOpacity(parcelFillOpacity(options.satellite)),
        );
      if (instance.getLayer("buildings"))
        instance.setPaintProperty(
          "buildings",
          "fill-opacity",
          options.satellite ? 0.1 : 0.48,
        );
      applyBuildingView(
        instance,
        options,
        options.buildings,
        activeRef.current?.geometry.type === "MultiPolygon"
          ? activeRef.current.id
          : null,
      );
    };
    if (instance.getSource("parcels")) update();
    else instance.once("load", update);
    return () => {
      instance.off("load", update);
    };
  }, [options]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const update = () =>
      setBuildingCamera(
        instance,
        options.dimension,
        window.matchMedia("(prefers-reduced-motion: reduce)").matches,
      );
    if (instance.getSource("parcels")) update();
    else instance.once("load", update);
    return () => {
      instance.off("load", update);
    };
  }, [options.dimension]);

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
        canvas.height = source.height + 184;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.drawImage(source, 0, 0);
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, source.height, canvas.width, 184);
        ctx.fillStyle = "#123c40";
        ctx.font = "18px sans-serif";
        ctx.fillText(
          `${brand.displayName} · ${locale === "ar" ? territory.name_ar : territory.name} · ${options.satellite ? (BASEMAP_IMAGERY.find((item) => item.id === options.scene)?.title ?? options.scene) : m.plan}`,
          16,
          source.height + 25,
        );
        ctx.font = "14px sans-serif";
        const legend = [
          ...(!options.satellite ? [[m.water, PLAN_COLORS.water]] : []),
          ...Object.entries(COLORS).map(([key, color]) => [
            m[key as Category],
            color,
          ]),
        ];
        legend.forEach(([title, color], i) => {
          const x = 16 + ((i % 4) * canvas.width) / 4,
            y = source.height + 48 + Math.floor(i / 4) * 26;
          ctx.fillStyle = color;
          ctx.fillRect(x, y, 13, 13);
          ctx.fillStyle = "#123c40";
          ctx.fillText(title, x + 19, y + 12, canvas.width / 4 - 35);
        });
        ctx.font = "12px sans-serif";
        ctx.fillText(
          [
            ...credits,
            ...(!options.satellite || options.dimension === "3d"
              ? [HYDROGRAPHY_CREDIT]
              : []),
          ].join(" · "),
          16,
          source.height + 142,
          canvas.width - 32,
        );
        if (options.satellite)
          ctx.fillText(
            BASEMAP_IMAGERY.find((item) => item.id === options.scene)
              ?.attribution ?? "",
            16,
            source.height + 168,
            canvas.width - 32,
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
  }, [
    view,
    m,
    options.satellite,
    options.scene,
    options.dimension,
    locale,
    territory,
    credits,
  ]);
  return (
    <>
      <section ref={element} className="parcel-map" aria-label={label} />
      <MapWorkbench
        map={toolMap}
        context={context}
        parcels={data}
        locale={locale}
        m={m}
        territory={territory.id}
        places={true}
        names={options.names}
        onChoose={(item) => {
          if (item.feature) callbacks.current.onFeature(item.feature);
          else if (item.parcelId) callbacks.current.onSelect(item.parcelId);
        }}
      />
      {imageryFailed && options.satellite && (
        <p className="map-imagery-error" role="alert">
          {m.imageryUnavailable}
        </p>
      )}
      {buildingsFailed &&
        options.dimension === "3d" &&
        options.buildingSource === "openstreetmap" && (
          <p className="map-imagery-error" role="alert">
            {m.threeDUnavailable}
          </p>
        )}
      <output
        ref={coordinates}
        className="map-coordinates"
        aria-label={m.coordinates}
      />
    </>
  );
}
