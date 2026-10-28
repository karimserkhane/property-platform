import type { components } from "@property-platform/contracts";

export type ProjectDetail = components["schemas"]["ProjectDetailResponse"];
export type ProjectMapLocation =
  components["schemas"]["ProjectMapLocationResponse"];
export type ProjectMedia = components["schemas"]["ProjectMediaResponse"];
export type ProjectSource = components["schemas"]["ProjectSourceResponse"];
export type ProjectLabels = Record<
  keyof typeof import("../../../messages/en.json").Project,
  string
>;
