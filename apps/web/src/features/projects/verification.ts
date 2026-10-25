import type { components } from "@property-platform/contracts";

export type ProjectVerification =
  components["schemas"]["ProjectVerificationResponse"];
export type VerificationContradiction =
  ProjectVerification["contradictions"][number];
export type VerificationLabels = Record<
  keyof typeof import("../../../messages/en.json").Verification,
  string
>;

const contradictionKeys = {
  announced_after_completion: "announcedAfterCompletion",
  announced_period_passed: "announcedPeriodPassed",
  sources_disagree: "sourcesDisagree",
  progress_decreased: "progressDecreased",
} as const;

/** Message keys of a contradiction; an unknown code is never shown under another name. */
export function contradictionKeysFor(code: string) {
  if (!Object.hasOwn(contradictionKeys, code)) return null;
  const title = contradictionKeys[code as keyof typeof contradictionKeys];
  return { title, note: `${title}Note` as `${typeof title}Note` } as const;
}

/** Identity of a contradiction: its code and the cited readings it puts side by side. */
export function contradictionKey(item: VerificationContradiction) {
  return JSON.stringify([
    item.code,
    item.announcements.map((point) => [
      point.source.url,
      point.first_observed_at,
    ]),
    item.register_readings.map((reading) => [
      reading.source.url,
      reading.first_observed_at,
    ]),
  ]);
}

/** Contradictions with a known code, each listed once, in API order. */
export function knownContradictions(verification: ProjectVerification) {
  const seen = new Set<string>();
  return verification.contradictions.filter((item) => {
    if (!contradictionKeysFor(item.code)) return false;
    const key = contradictionKey(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/** The sheet is only offered when the register or a reviewed link says something. */
export function hasVerification(
  verification: ProjectVerification | null | undefined,
): verification is ProjectVerification {
  return Boolean(
    verification &&
      (verification.latest_reading ||
        verification.register_readings.length ||
        verification.official_links.length ||
        verification.contradictions.length),
  );
}
