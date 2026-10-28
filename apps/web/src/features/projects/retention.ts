import type { components } from "@property-platform/contracts";

export type CancellationRetention =
  components["schemas"]["CancellationRetentionResponse"];
export type RetentionLabels = Record<
  keyof typeof import("../../../messages/en.json").Retention,
  string
>;

export function formatPercent(value: number, locale: string) {
  return new Intl.NumberFormat(locale, {
    style: "percent",
    maximumFractionDigits: 2,
  }).format(value / 100);
}

/**
 * Rates the cited schedule gives at the declared stage: one, two on a band limit the
 * commentaries leave open, none when the declared progress cannot be read.
 */
export function retentionRates(
  retention: CancellationRetention,
  locale: string,
) {
  if (retention.status !== "rate" && retention.status !== "boundary") return [];
  return retention.rates.map((rate) => formatPercent(rate, locale));
}
