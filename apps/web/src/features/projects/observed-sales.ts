import type { components } from "@property-platform/contracts";

export type ObservedSales =
  components["schemas"]["ProjectObservedSalesResponse"];
export type ObservedSalesGroup = ObservedSales["groups"][number];
export type ObservedRange = NonNullable<ObservedSalesGroup["price_aed"]>;
export type ObservedSalesLabels = Record<
  keyof typeof import("../../../messages/en.json").ObservedSales,
  string
>;

const applicationKeys = {
  "off-plan": "offPlan",
  ready: "ready",
  "court-mandated": "courtMandated",
} as const;

const sequenceKeys = {
  primary: "primary",
  secondary: "secondary",
} as const;

/** Message key of a closed ADREC value; an unknown value keeps its original text. */
export function saleApplicationKey(value: string) {
  return Object.hasOwn(applicationKeys, value)
    ? applicationKeys[value as keyof typeof applicationKeys]
    : null;
}

export function saleSequenceKey(value: string) {
  return Object.hasOwn(sequenceKeys, value)
    ? sequenceKeys[value as keyof typeof sequenceKeys]
    : null;
}

/** Both ends of a recorded range, or one value when they are equal; never an average. */
export function formatObservedRange(
  range: ObservedRange,
  format: (value: number) => string,
) {
  const low = Number(range.min);
  const high = Number(range.max);
  if (!Number.isFinite(low) || !Number.isFinite(high) || low > high)
    return null;
  return low === high ? format(low) : `${format(low)} – ${format(high)}`;
}

/** Sales of a partial share: counted, but outside the ranges. */
export function partialShareCount(group: ObservedSalesGroup) {
  return Math.max(0, group.sales_count - group.full_share_count);
}

/** Total recorded sales of the window, for the section navigation. */
export function observedSalesCount(sales: ObservedSales) {
  return sales.window
    ? sales.groups.reduce((total, group) => total + group.sales_count, 0)
    : 0;
}
