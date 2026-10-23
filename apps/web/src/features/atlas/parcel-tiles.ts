import type {
  ExpressionSpecification,
  LayerSpecification,
  Map as LibreMap,
  VectorSourceSpecification,
} from "maplibre-gl";
import type { ParcelIndex } from "./types";

// Footprints come from vector tiles keyed by parcel identity only. Category,
// visibility and labels come from the published `parcel-index` rows, so tiles
// never diverge from their recovery, classification and provenance rules.
// No relative value imports: this module stays testable with plain Node.
export const PARCEL_SOURCE = "parcels";
export const PARCEL_SOURCE_LAYER = "parcels";
export const PARCEL_LABEL_SOURCE = "parcel-labels";
const TILE_ZOOMS = { minzoom: 8, maxzoom: 16 } as const;

const FOOTPRINT_LAYERS = new Set(["parcel-fill", "parcel-line", "selection"]);
const LABEL_LAYERS = new Set([
  "parcel-project-names",
  "parcel-use-names",
  "parcel-codes",
]);
const CATEGORY: ExpressionSpecification = [
  "coalesce",
  ["feature-state", "category"],
  "unknown",
];
// Tiles can contain parcels the index has not listed (still loading, filtered
// out or beyond its budget); only listed parcels are drawn and selectable.
const SHOWN: ExpressionSpecification = [
  "boolean",
  ["feature-state", "shown"],
  false,
];

export function parcelTileSource(
  origin: string,
  territory: string,
): VectorSourceSpecification {
  return {
    type: "vector",
    tiles: [
      `${origin}/api/atlas/parcel-tiles/{z}/{x}/{y}?territory=${encodeURIComponent(territory)}`,
    ],
    ...TILE_ZOOMS,
    promoteId: "id",
  };
}

// Shared parcel paint reads `category` from feature state on tiles.
function fromState(value: unknown): unknown {
  if (!Array.isArray(value)) return value;
  if (value.length === 2 && value[0] === "get" && value[1] === "category")
    return CATEGORY;
  return value.map(fromState);
}

// Fill opacity for tiled parcels: the shared value, zero for unlisted parcels.
export function tiledParcelOpacity(
  opacity: number | ExpressionSpecification,
): ExpressionSpecification {
  return ["case", SHOWN, fromState(opacity) as ExpressionSpecification, 0];
}

export function tiledParcelLayers(
  layers: readonly LayerSpecification[],
): LayerSpecification[] {
  return layers.map((layer) => {
    if (LABEL_LAYERS.has(layer.id))
      return { ...layer, source: PARCEL_LABEL_SOURCE } as LayerSpecification;
    if (!FOOTPRINT_LAYERS.has(layer.id)) return layer;
    const tiled = {
      ...layer,
      "source-layer": PARCEL_SOURCE_LAYER,
    } as LayerSpecification & { paint?: Record<string, unknown> };
    if (layer.id === "parcel-fill")
      tiled.paint = {
        ...tiled.paint,
        "fill-color": fromState(tiled.paint?.["fill-color"]),
        "fill-opacity": tiledParcelOpacity(
          tiled.paint?.["fill-opacity"] as ExpressionSpecification,
        ),
      };
    if (layer.id === "parcel-line" || layer.id === "selection")
      tiled.paint = { ...tiled.paint, "line-opacity": ["case", SHOWN, 1, 0] };
    return tiled;
  });
}

// Applies listed rows as feature state; returns the identities now shown.
export function syncParcelStates(
  map: LibreMap,
  rows: ParcelIndex,
  previous: ReadonlySet<string>,
): Set<string> {
  const shown = new Set<string>();
  for (const feature of rows.features) {
    shown.add(feature.id);
    map.setFeatureState(
      {
        source: PARCEL_SOURCE,
        sourceLayer: PARCEL_SOURCE_LAYER,
        id: feature.id,
      },
      { shown: true, category: feature.properties.category },
    );
  }
  for (const id of previous)
    if (!shown.has(id))
      map.setFeatureState(
        { source: PARCEL_SOURCE, sourceLayer: PARCEL_SOURCE_LAYER, id },
        { shown: false },
      );
  return shown;
}

export function parcelLabelPoints(rows: ParcelIndex) {
  return {
    type: "FeatureCollection" as const,
    features: rows.features.map((feature) => ({
      type: "Feature" as const,
      id: feature.id,
      geometry: {
        type: "Point" as const,
        coordinates: [...feature.properties.label_point],
      },
      properties: feature.properties,
    })),
  };
}
