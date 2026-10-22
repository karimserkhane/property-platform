"use client";

import type { FeatureCollection } from "geojson";

import { Map as LibreMap, NavigationControl, setWorkerUrl } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { UiIcon } from "@/components/ui-icon";
import { HYDROGRAPHY_SOURCE, PLAN_COLORS } from "../atlas/hydrography";
import { MapLegend } from "../atlas/map-legend";
import {
  mapPlaceFilter,
  PROJECT_MARKER_IMAGE,
  registerMapMarkers,
} from "../atlas/map-markers";
import { mapControlLabels, mapLayers, mapName } from "../atlas/map-style";
import { readParcelPages } from "../atlas/parcel-pages";
import {
  geometryClickArea,
  parcelFillOpacity,
  parcelMapLabels,
  parcelPropertyIndex,
  propertyName,
  readableParcelCode,
  selectMapHit,
} from "../atlas/presentation";
import type { MapContext, MapLabels, UseLabels } from "../atlas/types";
import { projectLocationBounds } from "./neighbourhood-focus";
import { safeSourceUrl } from "./presentation";
import styles from "./project.module.css";
import type { ProjectMapLocation } from "./types";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Popup } from "maplibre-gl";
import { registerArchivedTiles } from "../atlas/archived-tiles";
import {
  applyBuildingView,
  type BuildingView,
  buildingViewSelection,
  setBuildingCamera,
} from "../atlas/building-3d";
import { showWorldBuilding } from "../atlas/building-popup";
import { BASEMAP_IMAGERY, imageryVisibility } from "../atlas/imagery-sources";
import { mapToolActive } from "../atlas/map-analysis";
import { MapViewControl } from "../atlas/map-view-control";
import { MapWorkbench } from "../atlas/map-workbench";
import {
  PROJECT_CLUSTER_LAYERS,
  zoomProjectCluster,
} from "../atlas/project-clusters";
import type { ParcelCollection } from "../atlas/types";

setWorkerUrl(
  new URL(
    "maplibre-gl/dist/maplibre-gl-worker.mjs",
    import.meta.url,
  ).toString(),
);

function updateView(
  map: LibreMap,
  options: BuildingView & {
    satellite: boolean;
    scene: string;
    commerce: boolean;
  },
) {
  for (const [id, visible] of Object.entries({
    ...imageryVisibility(options.satellite, options.scene),
    land: !options.satellite,
    "plan-water": !options.satellite,
    "plan-waterways": !options.satellite,
  }))
    if (map.getLayer(id))
      map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
  map.setPaintProperty(
    "parcel-fill",
    "fill-opacity",
    parcelFillOpacity(options.satellite),
  );
  applyBuildingView(map, options);
  for (const id of ["places", "place-names"])
    if (map.getLayer(id)) map.setFilter(id, mapPlaceFilter(options.commerce));
  if (map.getLayer("parcel-use-names"))
    map.setLayoutProperty("parcel-use-names", "visibility", "none");
  if (map.getLayer("parcel-project-names"))
    map.setLayoutProperty("parcel-project-names", "visibility", "none");
}

export default function NeighbourhoodMap({
  territory,
  bounds,
  locations,
  locale,
  label,
  mapLabels,
  unavailable,
  loadingLabel,
  retryLabel,
  useLabels,
  truncatedLabel,
}: {
  territory: string;
  bounds: number[];
  locations: ProjectMapLocation[];
  locale: string;
  label: string;
  mapLabels: MapLabels;
  unavailable: string;
  loadingLabel: string;
  retryLabel: string;
  useLabels: UseLabels;
  truncatedLabel: string;
}) {
  const root = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selection, setSelection] = useState<{
    title: string;
    code?: string;
    url: string | null;
  } | null>(null);
  const [truncated, setTruncated] = useState(false);
  const instance = useRef<LibreMap | null>(null);
  const [toolMap, setToolMap] = useState<LibreMap | null>(null);
  const [toolContext, setToolContext] = useState<MapContext | null>(null);
  const [toolParcels, setToolParcels] = useState<ParcelCollection | null>(null);
  const worldPopup = useRef<Popup | null>(null);
  const [viewOptions, setViewOptions] = useState(() => ({
    ...buildingViewSelection(null),
    satellite: false,
    scene: "esri",
    commerce: false,
  }));
  const viewRef = useRef(viewOptions);
  viewRef.current = viewOptions;

  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt retries the same bounded map read.
  useEffect(() => {
    if (!root.current) return;
    const abort = new AbortController();
    let map: LibreMap | undefined;
    let resize: ResizeObserver | undefined;
    setFailed(false);
    setLoading(true);
    setSelection(null);
    setTruncated(false);
    setToolMap(null);
    const extent: [[number, number], [number, number]] = [
      [bounds[0], bounds[1]],
      [bounds[2], bounds[3]],
    ];
    const projectExtent = projectLocationBounds(locations, bounds);
    const search = new URLSearchParams({
      territory,
      bbox: bounds.join(","),
    });
    const signal = AbortSignal.any([abort.signal, AbortSignal.timeout(15000)]);
    void Promise.all([
      fetch(`/api/atlas/map-context?${search}`, { signal }).then(
        async (response) => {
          if (!response.ok) throw new Error("unavailable");
          return (await response.json()) as MapContext;
        },
      ),
      readParcelPages(bounds.join(","), territory, signal),
    ])
      .then(([data, parcels]) => {
        if (abort.signal.aborted || !root.current) return;
        setToolContext(data);
        setToolParcels(parcels);
        const projectFeatures = projectExtent
          ? locations.map((location) => ({
              type: "Feature" as const,
              id: location.id,
              geometry: location.geometry,
              properties: { name: location.name, name_ar: "" },
            }))
          : [];
        setTruncated(
          parcels.truncated ||
            Object.values(data).some((layer) => layer.truncated),
        );
        registerArchivedTiles();
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
          maxPitch: 70,
          locale: mapControlLabels(mapLabels, label),
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
        });
        instance.current = map;
        map.addControl(
          new NavigationControl({ showCompass: true, visualizePitch: true }),
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
          map.addSource("hydrography", HYDROGRAPHY_SOURCE);
          for (const provider of BASEMAP_IMAGERY)
            map.addSource(provider.layerId, {
              type: "raster",
              tiles: [provider.tiles],
              tileSize: 256,
              minzoom: provider.minzoom,
              maxzoom: provider.maxzoom,
              attribution: provider.attribution,
            });
          setLoading(false);
          // Translate the derived use taxonomy; original evidence stays unchanged.
          const labelledParcels = parcelMapLabels(
            parcels,
            parcelPropertyIndex(data, parcels),
            locale,
            (key) => useLabels[key],
          );
          map.addSource("parcels", {
            type: "geojson",
            data: labelledParcels as unknown as FeatureCollection,
            attribution: [
              ...new Set(
                parcels.features
                  .map((feature) => feature.properties.source_name)
                  .filter((name): name is string => Boolean(name)),
              ),
            ].join(" · "),
          });
          for (const [key, collection] of Object.entries(data))
            map.addSource(key, {
              type: "geojson",
              data: collection as unknown as FeatureCollection,
              attribution:
                key === "building"
                  ? '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors · ODbL</a> · DMT / Onwani'
                  : key === "place"
                    ? '<a href="https://docs.overturemaps.org/attribution/">Overture Maps · upstream contributors</a>'
                    : undefined,
            });
          registerMapMarkers(map);
          for (const layer of mapLayers(locale).filter((layer) =>
            [
              ...BASEMAP_IMAGERY.map((provider) => provider.layerId),
              "land",
              "plan-water",
              "plan-waterways",
              "areas",
              "parcel-fill",
              "parcel-line",
              "parcel-project-names",
              "parcel-use-names",
              "buildings",
              "buildings-3d",
              "world-buildings-3d",
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
            map.addLayer(layer);
          }
          updateView(map, viewRef.current);
          setToolMap(map);
          setBuildingCamera(map, viewRef.current.dimension, true);
          const areas = new Map(
            parcels.features.map((item) => [
              item.id,
              geometryClickArea(item.geometry),
            ]),
          );
          map.on("click", (event) => {
            if (!map) return;
            if (mapToolActive(map) || zoomProjectCluster(map, event)) return;
            worldPopup.current?.remove();
            const projectLayers = [
              "project-point",
              "project-footprint",
              "project-name",
            ].filter((id) => map?.getLayer(id));
            if (
              projectLayers.length &&
              map.queryRenderedFeatures(event.point, { layers: projectLayers })
                .length
            ) {
              setSelection({
                title: projectFeatures[0].properties.name,
                url: null,
              });
              return;
            }
            const overWater =
              !viewRef.current.satellite &&
              map.queryRenderedFeatures(event.point, { layers: ["plan-water"] })
                .length > 0;
            const hit = selectMapHit(
              map
                .queryRenderedFeatures(event.point, {
                  layers: [
                    ...PROJECT_CLUSTER_LAYERS.filter(
                      (id) => id !== "cluster-projects" && map?.getLayer(id),
                    ),
                    "buildings",
                    "buildings-3d",
                    "places",
                    "project-names",
                    "place-names",
                    "streets",
                    "street-names",
                    "parcel-fill",
                    "parcel-project-names",
                    "parcel-use-names",
                  ],
                })
                .filter((hit) => !overWater || hit.source !== "parcels"),
              areas,
            );
            const projectHit = String(hit?.properties.kind).endsWith(
              "_project_marker",
            );
            if (
              !projectHit &&
              viewRef.current.dimension === "3d" &&
              viewRef.current.buildingSource === "openstreetmap"
            ) {
              const worldHit = map.queryRenderedFeatures(event.point, {
                layers: ["world-buildings-3d"],
              })[0];
              if (worldHit) {
                setSelection(null);
                worldPopup.current = showWorldBuilding(
                  map,
                  event.lngLat,
                  worldHit,
                  mapLabels,
                  locale,
                );
                return;
              }
            }
            if (!hit) {
              setSelection(null);
              return;
            }
            const id = String(hit.properties.id);
            if (hit.layer.id.startsWith("parcel-")) {
              const parcel = parcels.features.find((item) => item.id === id);
              if (parcel)
                setSelection({
                  title: parcel.properties.use_types?.[0]
                    ? useLabels[parcel.properties.use_types[0]]
                    : parcel.properties.land_use || mapLabels.parcelTitle,
                  code: parcel.properties.code,
                  url: safeSourceUrl(parcel.properties.source_url),
                });
            } else {
              const feature = [
                ...data.building.features,
                ...data.place.features,
                ...data.street.features,
              ].find((item) => item.id === id);
              if (feature)
                setSelection({
                  title:
                    propertyName(feature.properties, locale) ||
                    (feature.properties.use_types?.[0]
                      ? useLabels[feature.properties.use_types[0]]
                      : feature.geometry.type === "Point"
                        ? mapLabels.places
                        : feature.geometry.type === "MultiLineString"
                          ? mapLabels.streets
                          : mapLabels.building),
                  url: safeSourceUrl(feature.properties.source.url),
                });
            }
          });
          if (projectFeatures.length && projectExtent) {
            map.addSource("project", {
              type: "geojson",
              data: {
                type: "FeatureCollection",
                features: projectFeatures,
              } as unknown as FeatureCollection,
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
              type: "symbol",
              source: "project",
              filter: ["==", ["geometry-type"], "Point"],
              layout: {
                "icon-image": PROJECT_MARKER_IMAGE,
                "icon-size": 1.4,
                "icon-allow-overlap": true,
                "icon-ignore-placement": true,
                "icon-pitch-alignment": "viewport",
                "icon-rotation-alignment": "viewport",
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
      worldPopup.current?.remove();
      setToolMap(null);
      instance.current = null;
      map?.remove();
    };
  }, [
    attempt,
    bounds,
    territory,
    locations,
    locale,
    label,
    mapLabels,
    useLabels,
  ]);
  useEffect(() => {
    const map = instance.current;
    if (!map?.getLayer("buildings-3d")) return;
    worldPopup.current?.remove();
    updateView(map, viewOptions);
  }, [viewOptions]);
  useEffect(() => {
    const map = instance.current;
    if (map?.getLayer("buildings-3d"))
      setBuildingCamera(
        map,
        viewOptions.dimension,
        window.matchMedia("(prefers-reduced-motion: reduce)").matches,
      );
  }, [viewOptions.dimension]);
  return (
    <section
      className={styles.localMap}
      aria-label={label}
      aria-busy={loading && !failed}
    >
      <div ref={root} className={styles.localCanvas} />
      {!failed && (
        <MapWorkbench
          map={toolMap}
          context={toolContext}
          parcels={toolParcels}
          locale={locale}
          m={mapLabels}
          territory={territory}
          onChoose={(item) => {
            setSelection({
              title: item.name,
              url: item.feature
                ? safeSourceUrl(item.feature.properties.source.url)
                : null,
            });
          }}
          compact
        />
      )}
      {!failed && (
        <div className={styles.localView}>
          <MapViewControl
            satellite={viewOptions.satellite}
            scene={viewOptions.scene}
            buildingView={viewOptions}
            m={mapLabels}
            sourceLabel={mapLabels.reference}
            locale={locale}
            onChange={(satellite, scene) =>
              setViewOptions((value) => ({ ...value, satellite, scene }))
            }
            commerce={viewOptions.commerce}
            onCommerceChange={(commerce) =>
              setViewOptions((value) => ({ ...value, commerce }))
            }
            onBuildingViewChange={(value) =>
              setViewOptions((previous) => ({ ...previous, ...value }))
            }
          />
        </div>
      )}
      {loading && !failed && (
        <p className={styles.mapLoading} role="status">
          {loadingLabel}
        </p>
      )}
      {!failed && (
        <MapLegend
          className={styles.localLegend}
          m={mapLabels}
          context={toolContext}
          options={viewOptions}
        />
      )}
      {selection && !failed && (
        <aside className={styles.localSelection} aria-live="polite">
          <button
            type="button"
            aria-label={mapLabels.closeDetails}
            onClick={() => setSelection(null)}
          >
            <UiIcon name="close" />
          </button>
          <h3 className={styles.localTitle}>
            <bdi>{selection.title}</bdi>
          </h3>
          {selection.code && (
            <p>
              <bdi>{readableParcelCode(selection.code)}</bdi>
            </p>
          )}
          {selection.url && (
            <a href={selection.url} target="_blank" rel="noopener noreferrer">
              {mapLabels.reference} ↗
            </a>
          )}
        </aside>
      )}
      {truncated && !failed && (
        <p className={styles.localNotice} role="status">
          {truncatedLabel}
        </p>
      )}
      {failed && (
        <div className={styles.mapError} role="status">
          <p>{unavailable}</p>
          <button
            className={styles.primaryAction}
            type="button"
            onClick={() => setAttempt((value) => value + 1)}
          >
            {retryLabel}
          </button>
        </div>
      )}
    </section>
  );
}
