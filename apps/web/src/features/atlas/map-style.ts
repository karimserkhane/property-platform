import type { ExpressionSpecification, LayerSpecification } from "maplibre-gl";
import { COLORS } from "./presentation";
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
  return [
    {
      id: "satellite",
      type: "raster",
      source: "satellite",
      layout: { visibility: "none" },
    },
    {
      id: "land",
      type: "fill",
      source: "administrative_area",
      filter: ["==", ["get", "kind"], "district"],
      paint: { "fill-color": "#f4f6f3" },
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
        "fill-color": [
          "match",
          ["get", "category"],
          "mixed",
          COLORS.mixed,
          "residential",
          COLORS.residential,
          "green",
          COLORS.green,
          "public",
          COLORS.public,
          "tech",
          COLORS.tech,
          "rail",
          COLORS.rail,
          "overlay",
          COLORS.overlay,
          "#e7e3d7",
        ],
        "fill-opacity": [
          "case",
          ["==", ["get", "category"], "overlay"],
          0.15,
          0.86,
        ],
      },
    },
    {
      id: "parcel-line",
      type: "line",
      source: "parcels",
      paint: { "line-color": "#8f9fa0", "line-width": 0.6 },
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
      id: "places",
      type: "circle",
      source: "place",
      paint: {
        "circle-color": [
          "case",
          ["==", ["get", "kind"], "publisher_project_marker"],
          "#eb7939",
          "#246b71",
        ],
        "circle-radius": 4,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1.5,
      },
    },
    {
      id: "place-names",
      type: "symbol",
      source: "place",
      minzoom: 11.5,
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
