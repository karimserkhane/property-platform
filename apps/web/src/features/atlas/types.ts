import type { components } from "@property-platform/contracts";

export type ParcelCollection = components["schemas"]["Collection"];
// Footprint-free rows; the explorer draws parcels from vector tiles.
export type ParcelIndex = components["schemas"]["ParcelIndex"];
export type ParcelIndexFeature = ParcelIndex["features"][number];
// Either collection shape: code needing footprints checks for `geometry`.
export type ParcelRows = ParcelCollection | ParcelIndex;
export type ParcelDetail = components["schemas"]["Detail"];
export type MapContext = components["schemas"]["MapContext"];
// Streets and buildings with bounds only; the explorer draws them from tiles.
export type ContextIndex = components["schemas"]["ContextIndex"];
export type ContextIndexFeature = ContextIndex["building"]["features"][number];
export type MapFeature = components["schemas"]["MapFeature"];
export type ResearchReference =
  components["schemas"]["ResearchReferenceResponse"];
export type ImageryScene = components["schemas"]["ImageryResponse"];
export type Territory = components["schemas"]["TerritoryResponse"];
export type TerritoryRegistry = components["schemas"]["TerritoryRegistry"];
export type CoverageLabels = Record<
  keyof typeof import("../../../messages/en.json").Coverage,
  string
>;
export type MapLabels = Record<
  keyof typeof import("../../../messages/en.json").Map,
  string
>;
export type UseLabels = typeof import("../../../messages/en.json").Use;
export type AtlasLabels = Record<
  | "explore"
  | "sources"
  | "pilot"
  | "intro"
  | "search"
  | "reference"
  | "loading"
  | "unavailable"
  | "retry"
  | "empty"
  | "truncated"
  | "select"
  | "source"
  | "retrieved"
  | "published"
  | "unknown"
  | "district"
  | "community"
  | "limitations"
  | "list"
  | "map"
  | "reset"
  | "count"
  | "back",
  string
>;
