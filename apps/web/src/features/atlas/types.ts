import type { components } from "@property-platform/contracts";

export type ParcelCollection = components["schemas"]["Collection"];
export type ParcelDetail = components["schemas"]["Detail"];
export type MapContext = components["schemas"]["MapContext"];
export type MapFeature = components["schemas"]["MapFeature"];
export type ResearchReference =
  components["schemas"]["ResearchReferenceResponse"];
export type ImageryScene = components["schemas"]["ImageryResponse"];
export type MapLabels = Record<
  keyof typeof import("../../../messages/en.json").Map,
  string
>;
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
