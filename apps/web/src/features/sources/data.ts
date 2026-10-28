import type { components } from "@property-platform/contracts";

export type SourceSite = components["schemas"]["SourceSiteRightsResponse"];
// `reviewedCount` takes values, so the page formats it.
export type SourcesLabels = Record<
  Exclude<
    keyof typeof import("../../../messages/en.json").Sources,
    "reviewedCount"
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
