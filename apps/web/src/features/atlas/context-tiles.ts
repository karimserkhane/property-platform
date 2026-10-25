import type {
  LayerSpecification,
  Map as LibreMap,
  VectorSourceSpecification,
} from "maplibre-gl";
import type { ShadowBuilding } from "./solar";
import type { AtlasContext, ContextIndex, IndexedFeature } from "./types";

// Building and street shapes come from vector tiles keyed by identity (streets
// also carry the display names their line labels need). Heights and the rows
// behind selection, cards and credits come from the published `context-index`,
// as for parcels. No relative value imports: testable with plain Node.
export const CONTEXT_SOURCE = "context";
export const CONTEXT_FAMILIES = ["building", "street"] as const;
type Family = (typeof CONTEXT_FAMILIES)[number];
const TILE_ZOOMS = { minzoom: 11, maxzoom: 16 } as const;
// Index attributes that paint reads from feature state on tiles.
const STATE_ATTRIBUTES = new Set(["height_m", "levels"]);

export function contextTileSource(
  origin: string,
  territory: string,
): VectorSourceSpecification {
  return {
    type: "vector",
    tiles: [
      `${origin}/api/atlas/context-tiles/{z}/{x}/{y}?territory=${encodeURIComponent(territory)}`,
    ],
    ...TILE_ZOOMS,
    promoteId: "id",
  };
}

function fromState(value: unknown): unknown {
  if (!Array.isArray(value)) return value;
  if (
    value.length === 2 &&
    value[0] === "get" &&
    STATE_ATTRIBUTES.has(value[1] as string)
  )
    return ["feature-state", value[1]];
  return value.map(fromState);
}

// Moves the shared building and street layers onto the tile source; their
// paint reads index attributes from feature state.
export function tiledContextLayers(
  layers: readonly LayerSpecification[],
): LayerSpecification[] {
  return layers.map((layer) => {
    const source = "source" in layer ? layer.source : undefined;
    if (!CONTEXT_FAMILIES.includes(source as Family)) return layer;
    const paint = Object.fromEntries(
      Object.entries(("paint" in layer ? layer.paint : undefined) ?? {}).map(
        ([key, value]) => [key, fromState(value)],
      ),
    );
    return {
      ...layer,
      source: CONTEXT_SOURCE,
      "source-layer": source,
      paint,
    } as LayerSpecification;
  });
}

// Applies index rows as feature state; returns the identities now listed.
export function syncContextStates(
  map: LibreMap,
  index: Pick<AtlasContext, Family>,
  previous: ReadonlyMap<string, Family>,
): Map<string, Family> {
  const listed = new Map<string, Family>();
  for (const family of CONTEXT_FAMILIES)
    for (const feature of index[family].features) {
      listed.set(feature.id, family);
      map.setFeatureState(
        { source: CONTEXT_SOURCE, sourceLayer: family, id: feature.id },
        {
          height_m: feature.properties.height_m ?? null,
          levels: feature.properties.levels ?? null,
        },
      );
    }
  for (const [id, family] of previous)
    if (!listed.has(id))
      map.removeFeatureState({
        source: CONTEXT_SOURCE,
        sourceLayer: family,
        id,
      });
  return listed;
}

// Tags index rows with their tile layer for code shared with `map-context`.
export function indexedContext(index: ContextIndex): AtlasContext {
  const tag = (family: Family) => ({
    ...index[family],
    features: index[family].features.map(
      (feature): IndexedFeature => ({ ...feature, family }),
    ),
  });
  return {
    street: tag("street"),
    building: tag("building"),
    place: index.place,
    administrative_area: index.administrative_area,
  };
}

// Listed buildings with a recorded height, for "recorded heights only" in 3D.
export function recordedBuildings(
  context: Pick<AtlasContext, "building"> | null,
): string[] {
  return (context?.building.features ?? [])
    .filter(
      ({ properties: { height_m } }) =>
        typeof height_m === "number" &&
        Number.isFinite(height_m) &&
        height_m > 0 &&
        height_m <= 1500,
    )
    .map((feature) => feature.id);
}

// Footprints of listed buildings on loaded tiles with their index heights, for
// shadow estimates. A building split by tile edges yields one piece per tile.
export function tiledFootprints(
  map: LibreMap,
  context: Pick<AtlasContext, "building"> | null,
): ShadowBuilding[] {
  if (!map.getSource(CONTEXT_SOURCE)) return [];
  const heights = new Map(
    (context?.building.features ?? []).map((feature) => [
      feature.id,
      feature.properties.height_m,
    ]),
  );
  const footprints: ShadowBuilding[] = [];
  for (const tile of map.querySourceFeatures(CONTEXT_SOURCE, {
    sourceLayer: "building",
  })) {
    const id = String(tile.properties.id);
    const geometry = tile.geometry;
    if (!heights.has(id)) continue;
    const coordinates =
      geometry.type === "Polygon"
        ? [geometry.coordinates]
        : geometry.type === "MultiPolygon"
          ? geometry.coordinates
          : null;
    if (coordinates)
      footprints.push({
        id,
        geometry: { type: "MultiPolygon", coordinates },
        properties: { height_m: heights.get(id) },
      });
  }
  return footprints;
}
