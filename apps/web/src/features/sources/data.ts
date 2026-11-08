import type { components } from "@property-platform/contracts";

export type SourceSite = components["schemas"]["SourceSiteRightsResponse"];
export type SourceFamily =
  components["schemas"]["SourceFamilyFreshnessResponse"];
// These take values, so the page formats them.
export type SourcesLabels = Record<
  Exclude<
    keyof typeof import("../../../messages/en.json").Sources,
    "reviewedCount" | "behindSources"
  >,
  string
>;

type PreviewReader = (
  path: string,
) => Promise<{ status: number; data: unknown }>;

const collection = new Set(["allowed", "forbidden"]);
const publication = new Set(["open", "facts", "link", "none"]);

function isSite(site: unknown): site is SourceSite {
  const row = site as SourceSite | null;
  return (
    !!row &&
    typeof row.host === "string" &&
    typeof row.publisher === "string" &&
    typeof row.licence === "string" &&
    collection.has(row.collection) &&
    publication.has(row.publication)
  );
}

/** The reviewed source rights registry (A19), as the API publishes it. */
export async function readSourceSitesData(read: PreviewReader) {
  try {
    const result = await read("source-rights");
    if (result.status !== 200) return { status: result.status, sites: null };
    const items = (result.data as { items?: unknown } | null)?.items;
    if (!Array.isArray(items) || !items.every(isSite))
      return { status: 503, sites: null };
    return { status: 200, sites: items };
  } catch {
    return { status: 503, sites: null };
  }
}

const familyLabels = {
  "developer-pages": "familyDeveloperPages",
  "adrec-register": "familyAdrecRegister",
  "adrec-market": "familyAdrecMarket",
  "parcels-onwani": "familyParcelsOnwani",
  "parcels-adsdi": "familyParcelsAdsdi",
  osm: "familyOsm",
  overture: "familyOverture",
  "public-context": "familyPublicContext",
  "sentinel-2": "familySentinel",
  "evidence-search": "familyEvidenceSearch",
} as const;

export type KnownFamily = SourceFamily & { family: keyof typeof familyLabels };

function isKnownFamily(row: SourceFamily): row is KnownFamily {
  return Object.hasOwn(familyLabels, row.family);
}

const optionalDate = (value: unknown) =>
  value === null || value === undefined || typeof value === "string";

function isFamily(row: unknown): row is SourceFamily {
  const family = row as SourceFamily | null;
  return (
    !!family &&
    typeof family.family === "string" &&
    typeof family.sources_total === "number" &&
    typeof family.sources_behind === "number" &&
    optionalDate(family.last_success_at) &&
    optionalDate(family.late_from) &&
    optionalDate(family.review_from)
  );
}

/** Freshness of each reviewed family; the sources page stays useful without it. */
export async function readSourceFreshnessData(read: PreviewReader) {
  try {
    const result = await read("source-freshness");
    const families = (result.data as { families?: unknown } | null)?.families;
    if (
      result.status !== 200 ||
      !Array.isArray(families) ||
      !families.every(isFamily)
    )
      return { families: null };
    // A family this build has no label for is left out rather than shown untranslated.
    return { families: families.filter(isKnownFamily) };
  } catch {
    return { families: null };
  }
}

export function familyLabelKey(family: KnownFamily["family"]) {
  return familyLabels[family];
}

const stateKeys = {
  current: "freshnessCurrent",
  late: "freshnessLate",
  review: "freshnessReview",
  never: "freshnessNever",
} as const;

/** Read against the reader's clock: the API's answer stays valid while time passes. */
export function freshnessState(family: SourceFamily, now: Date) {
  if (!family.last_success_at || !family.late_from || !family.review_from)
    return "never";
  if (now >= new Date(family.review_from)) return "review";
  return now >= new Date(family.late_from) ? "late" : "current";
}

export function freshnessLabelKey(state: keyof typeof stateKeys) {
  return stateKeys[state];
}

const publicationKeys = {
  open: "publicationOpen",
  facts: "publicationFacts",
  link: "publicationLink",
  none: "publicationNone",
} as const;

export function publicationLabelKey(level: SourceSite["publication"]) {
  return publicationKeys[level];
}

/** Sites with a review first, then by publisher, in the reader's language. */
export function sortSourceSites(sites: SourceSite[], locale: string) {
  const collator = new Intl.Collator(locale);
  return [...sites].sort(
    (a, b) =>
      Number(!a.reviewed_on) - Number(!b.reviewed_on) ||
      collator.compare(a.publisher, b.publisher) ||
      collator.compare(a.host, b.host),
  );
}
