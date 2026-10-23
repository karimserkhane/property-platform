import type { ExpressionSpecification, LayerSpecification } from "maplibre-gl";
import { building3DLayers } from "./building-3d";
import { HYDROGRAPHY_LAYERS, PLAN_COLORS } from "./hydrography";
import { BASEMAP_IMAGERY } from "./imagery-sources";
import {
  mapMarkerImage,
  mapPlaceFilter,
  PROJECT_MARKER_FILTER,
} from "./map-markers";
import { parcelFillColor, parcelFillOpacity } from "./presentation";
import type { MapLabels } from "./types";

export function mapControlLabels(labels: MapLabels, title: string) {
  return {
    "Map.Title": title,
    "NavigationControl.ZoomIn": labels.zoomIn,
    "NavigationControl.ZoomOut": labels.zoomOut,
    "NavigationControl.ResetBearing": labels.resetBearing,
    "AttributionControl.ToggleAttribution": labels.toggleAttribution,
  };
}

const fonts = ["Arial", "Noto Sans", "sans-serif"];
export function mapName(locale: string): ExpressionSpecification {
  return [
    "case",
    ["all", ["==", locale, "ar"], ["!=", ["get", "name_ar"], ""]],
    ["get", "name_ar"],
    ["get", "name"],
  ];
}

export function mapLayers(locale: string): LayerSpecification[] {
  const name = mapName(locale);
  const project = PROJECT_MARKER_FILTER;
  return [
    ...BASEMAP_IMAGERY.map(
      ({ layerId }): LayerSpecification => ({
        id: layerId,
        type: "raster",
        source: layerId,
        layout: { visibility: "none" },
        paint: { "raster-fade-duration": 150 },
      }),
    ),
    {
      id: "land",
      type: "fill",
      source: "administrative_area",
      filter: ["==", ["get", "kind"], "district"],
      paint: { "fill-color": PLAN_COLORS.land },
    },
    {
      id: "area-hit",
      type: "fill",
      source: "administrative_area",
      paint: { "fill-opacity": 0 },
    },
    {
      id: "areas",
      type: "line",
      source: "administrative_area",
      paint: {
        "line-color": "#779ba0",
        "line-width": 1,
        "line-dasharray": [4, 3],
      },
    },
    {
      id: "parcel-fill",
      type: "fill",
      source: "parcels",
      paint: {
        "fill-color": parcelFillColor(),
        "fill-opacity": parcelFillOpacity(false),
      },
    },
    {
      id: "parcel-line",
      type: "line",
      source: "parcels",
      paint: { "line-color": "#8f9fa0", "line-width": 0.6 },
    },
    // Source cadastre can extend beyond the basemap coast (planned land, marinas).
    // Water covers the solid parcel surfaces and outlines so the sea is never
    // painted; the expert toggle restores solid outlines above it.
    ...HYDROGRAPHY_LAYERS,
    // OSM coastlines lag behind reclamation: whole planned districts (Saadiyat
    // villas, parks, substations) lie in mapped "ocean". A faint tint and a
    // dashed outline above the water keep those surveyed plots readable instead
    // of cutting them at the coast. Project perimeters stay hidden over water.
    {
      id: "parcel-water-fill",
      type: "fill",
      source: "parcels",
      paint: {
        "fill-color": parcelFillColor(),
        "fill-opacity": [
          "case",
          ["==", ["get", "category"], "overlay"],
          0,
          0.28,
        ],
      },
    },
    {
      id: "parcel-water-line",
      type: "line",
      source: "parcels",
      paint: {
        "line-color": "#8f9fa0",
        "line-width": 0.6,
        "line-dasharray": [2, 2],
        "line-opacity": ["case", ["==", ["get", "category"], "overlay"], 0, 1],
      },
    },
    {
      id: "buildings",
      type: "fill",
      source: "building",
      minzoom: 11.5,
      paint: {
        "fill-color": "#688783",
        "fill-opacity": 0.48,
        "fill-outline-color": "#496d67",
      },
    },
    ...building3DLayers(),
    {
      id: "street-casing",
      type: "line",
      source: "street",
      paint: {
        "line-color": "#a4b8bd",
        "line-width": ["interpolate", ["linear"], ["zoom"], 12, 1.4, 17, 7],
      },
    },
    {
      id: "streets",
      type: "line",
      source: "street",
      paint: {
        "line-color": "#ffffff",
        "line-width": ["interpolate", ["linear"], ["zoom"], 12, 1, 17, 5],
      },
    },
    {
      id: "street-names",
      type: "symbol",
      source: "street",
      minzoom: 12.5,
      layout: {
        "symbol-placement": "line",
        "text-field": name,
        "text-font": fonts,
        "text-size": 11,
        "text-max-angle": 40,
      },
      paint: {
        "text-color": "#315e69",
        "text-halo-color": "#ffffff",
        "text-halo-width": 2,
      },
    },
    {
      id: "project-halo",
      type: "circle",
      source: "place",
      filter: project,
      paint: {
        "circle-radius": 13,
        "circle-color": "#eb7939",
        "circle-opacity": 0.16,
        "circle-radius-transition": { duration: 0 },
        "circle-opacity-transition": { duration: 0 },
      },
    },
    {
      id: "places",
      type: "symbol",
      source: "place",
      minzoom: 14.5,
      filter: mapPlaceFilter(),
      layout: {
        "icon-image": mapMarkerImage(),
        "icon-size": ["interpolate", ["linear"], ["zoom"], 13.5, 0.7, 16, 0.9],
        "icon-padding": 3,
        "icon-pitch-alignment": "viewport",
        "icon-rotation-alignment": "viewport",
      },
    },
    {
      id: "project-names",
      type: "symbol",
      source: "place",
      minzoom: 11.5,
      filter: project,
      layout: {
        "text-field": name,
        "text-font": fonts,
        "text-size": 13,
        "text-max-width": 17,
        "text-variable-anchor": ["top", "bottom", "left", "right"],
        "text-radial-offset": 0.7,
      },
      paint: {
        "text-color": "#234c56",
        "text-halo-color": "#ffffff",
        "text-halo-width": 2,
      },
    },
    {
      id: "place-names",
      type: "symbol",
      source: "place",
      minzoom: 15,
      filter: mapPlaceFilter(),
      layout: {
        "text-field": name,
        "text-font": fonts,
        "text-size": 11,
        "text-max-width": 13,
        "text-variable-anchor": ["top", "bottom", "left", "right"],
        "text-radial-offset": 0.7,
      },
      paint: {
        "text-color": "#234c56",
        "text-halo-color": "#ffffff",
        "text-halo-width": 2,
      },
    },
    ...(["project", "use"] as const).map(
      (kind): LayerSpecification => ({
        id: `parcel-${kind}-names`,
        type: "symbol",
        source: "parcels",
        minzoom: kind === "project" ? 13.5 : 15.3,
        filter: [
          "all",
          ["!=", ["get", "display_name"], ""],
          ["==", ["get", "potential_name"], kind === "project"],
        ],
        layout: {
          "text-field": ["get", "display_name"],
          "text-font": fonts,
          "text-size": kind === "project" ? 12 : 10,
          "text-max-width": 14,
          "text-padding": 7,
        },
        paint: {
          "text-color": kind === "project" ? "#123e46" : "#3e5b63",
          "text-halo-color": "#fffffff2",
          "text-halo-width": 2.5,
        },
      }),
    ),
    {
      id: "parcel-codes",
      type: "symbol",
      source: "parcels",
      minzoom: 15,
      layout: {
        visibility: "none",
        "text-field": ["get", "code"],
        "text-font": fonts,
        "text-size": 10,
      },
      paint: {
        "text-color": "#3c5e63",
        "text-halo-color": "white",
        "text-halo-width": 1.5,
      },
    },
    {
      id: "area-names",
      type: "symbol",
      source: "administrative_area",
      maxzoom: 15,
      layout: { "text-field": name, "text-font": fonts, "text-size": 14 },
      paint: {
        "text-color": "#325b65",
        "text-halo-color": "white",
        "text-halo-width": 2,
      },
    },
    {
      id: "selection",
      type: "line",
      source: "parcels",
      filter: ["==", ["get", "id"], ""],
      paint: { "line-color": "#eb7939", "line-width": 3 },
    },
    {
      id: "area-selection",
      type: "line",
      source: "administrative_area",
      filter: ["==", ["get", "id"], ""],
      paint: { "line-color": "#eb7939", "line-width": 3 },
    },
    {
      id: "building-selection",
      type: "line",
      source: "building",
      filter: ["==", ["get", "id"], ""],
      paint: { "line-color": "#eb7939", "line-width": 4 },
    },
    {
      id: "place-selection",
      type: "circle",
      source: "place",
      filter: ["==", ["get", "id"], ""],
      paint: {
        "circle-radius": 10,
        "circle-color": "#eb793922",
        "circle-stroke-color": "#eb7939",
        "circle-stroke-width": 3,
      },
    },
    {
      id: "street-selection",
      type: "line",
      source: "street",
      filter: ["==", ["get", "id"], ""],
      paint: { "line-color": "#eb7939", "line-width": 4 },
    },
  ];
}
