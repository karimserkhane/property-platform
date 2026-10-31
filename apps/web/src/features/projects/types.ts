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
export type SourceRights = components["schemas"]["SourceRightsResponse"];
// The Project texts every citation of a source needs, wherever it is shown (A20, A24).
export const SOURCE_RIGHTS_LABELS = [
  "rightsLicence",
  "rightsUnreviewed",
  "rightsReserved",
  "rightsPerItem",
  "rightsTerms",
  "rightsBeyondLink",
  "rightsBeyondNone",
] as const satisfies readonly (keyof ProjectLabels)[];
export type SourceRightsLabels = Pick<
  ProjectLabels,
  (typeof SOURCE_RIGHTS_LABELS)[number]
>;
