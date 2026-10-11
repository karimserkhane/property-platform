import type { components } from "@liwa/contracts";

export type ParcelCollection = components["schemas"]["Collection"];
export type ParcelDetail = components["schemas"]["Detail"];
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
