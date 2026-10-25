import type { components } from "@property-platform/contracts";

export type ProjectActivity =
  components["schemas"]["ProjectConstructionActivityResponse"];
export type ActivityParcel = ProjectActivity["parcels"][number];
export type ActivityLabels = Record<
  keyof typeof import("../../../messages/en.json").Activity,
  string
>;

const levelKeys = {
  low: "levelLow",
  moderate: "levelModerate",
  high: "levelHigh",
} as const;

const basisKeys = {
  cadastral_parcel: "basisReviewedParcel",
  authority_point: "basisAuthorityPoint",
  building_footprint: "basisBuildingFootprint",
} as const;

/** What can be said about a parcel; an unknown status or level says nothing. */
export function activityState(parcel: ActivityParcel) {
  const latest = parcel.latest;
  if (latest.status === "insufficient_clear_pixels" && latest.level === null)
    return { kind: "insufficient", latest } as const;
  if (
    latest.status === "measured" &&
    latest.level !== null &&
    Object.hasOwn(levelKeys, latest.level)
  )
    return {
      kind: "measured",
      latest,
      level: levelKeys[latest.level],
    } as const;
  return null;
}

/** Message key of the reason the parcel stands for the project. */
export function activityBasisKey(parcel: ActivityParcel) {
  const derived = parcel.area_basis === "parcel_containing_position";
  if (derived === (parcel.position_method === "cadastral_parcel")) return null;
  return Object.hasOwn(basisKeys, parcel.position_method)
    ? basisKeys[parcel.position_method]
    : null;
}

/** Parcel area in hectares, as a size, never as a measured result. */
export function formatHectares(areaM2: number, locale: string) {
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: areaM2 < 10_000 ? 2 : 1,
  }).format(areaM2 / 10_000);
}

/** Parcels the sheet can describe, in API order. */
export function describedParcels(activity: ProjectActivity) {
  return activity.parcels.filter(
    (parcel) => activityState(parcel) && activityBasisKey(parcel),
  );
}
