import type { ProjectDetail, ProjectMedia, ProjectSource } from "./types";

// Field-specific notes and pointers never belong in buyer-facing source citations.
// Group by capture provenance, preserving separate source versions and history.
export function projectEvidenceSources(sources: ProjectSource[]) {
  const unique = new Map<string, { key: string; source: ProjectSource }>();
  for (const source of sources) {
    const key = JSON.stringify([
      source.url,
      source.name,
      source.kind,
      source.language,
      source.content_sha256,
      source.retrieved_at,
      source.published_at,
      source.ingested_at,
      source.historical,
      source.rights_status,
      source.developer_name,
      source.developer_role,
    ]);
    if (!unique.has(key)) unique.set(key, { key, source });
  }
  return [...unique.values()];
}

export function formatProjectDate(value: string, locale: string) {
  const date = new Date(value);
  return Number.isFinite(date.getTime())
    ? new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeZone: "Asia/Dubai",
      }).format(date)
    : null;
}

const amenityKeys = {
  swimming_pool: "amenityPool",
  children_pool: "amenityChildrenPool",
  children_play_area: "amenityPlayArea",
  gym: "amenityGym",
  seating_area: "amenitySeating",
  retail: "amenityRetail",
  landscaped_gardens: "amenityGardens",
  barbecue_area: "amenityBarbecue",
  parking: "amenityParking",
  restaurants: "amenityRestaurants",
  security: "amenitySecurity",
} as const;

export function projectAmenityKey(code: string) {
  return Object.hasOwn(amenityKeys, code)
    ? amenityKeys[code as keyof typeof amenityKeys]
    : null;
}

type Typology = ProjectDetail["typologies"][number];
type TypologyGroup = {
  property_type: string;
  bedrooms: number[];
  claims: Typology[];
};

// A compact display groups only explicit claims for the same property type.
// Generic claims do not add bedroom counts, and all source assertions survive.
export function groupProjectTypologies(
  typologies: Typology[],
): TypologyGroup[] {
  const groups = new Map<string, TypologyGroup>();
  for (const claim of typologies) {
    let group = groups.get(claim.property_type);
    if (!group) {
      group = { property_type: claim.property_type, bedrooms: [], claims: [] };
      groups.set(claim.property_type, group);
    }
    group.claims.push(claim);
    if (
      claim.bedrooms != null &&
      Number.isInteger(claim.bedrooms) &&
      claim.bedrooms >= 0 &&
      !group.bedrooms.includes(claim.bedrooms)
    )
      group.bedrooms.push(claim.bedrooms);
  }
  return [...groups.values()].map((group) => ({
    ...group,
    bedrooms: group.bedrooms.toSorted((a, b) => a - b),
  }));
}

// A developer-like hostname or an unverified URL alone is not first-party evidence.
export function projectWebsite(
  project: Pick<ProjectDetail, "website_url" | "sources">,
) {
  const url = safeSourceUrl(project.website_url);
  const source = url
    ? project.sources.find((item) => safeSourceUrl(item.url) === url)
    : undefined;
  return {
    url,
    official:
      !!source && ["developer", "publisher"].includes(source.kind ?? ""),
  };
}

// Both the map preview and full dossier use the same rights-aware selection.
export function projectMedia(project: Pick<ProjectDetail, "media">) {
  const visible = project.media.filter(
    (item) => item.rights_status !== "blocked",
  );
  const isDocument = (item: ProjectMedia) =>
    item.kind === "document" ||
    ["floor_plan", "brochure", "factsheet"].includes(item.role);
  const images = visible.filter(
    (item) => !isDocument(item) && playableMedia(item) === "image",
  );
  const hero = images.find((item) => item.role === "hero") ?? images[0] ?? null;
  return {
    hero,
    documents: visible.filter(isDocument),
    visuals: visible.filter((item) => !isDocument(item)),
  };
}

// The reviewed role identifies a plan; an image MIME type alone cannot do so.
export function mediaLabel(media: Pick<ProjectMedia, "role" | "kind">) {
  if (media.role === "floor_plan") return "floorPlans";
  if (media.role === "brochure") return "brochure";
  if (media.role === "factsheet") return "factsheet";
  return media.kind;
}

const MEDIA_ROUTE =
  /^\/api\/atlas\/project-media\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function safeSourceUrl(value: string | null | undefined): string | null {
  if (
    !value ||
    value.trim() !== value ||
    [...value].some((character) => {
      const code = character.codePointAt(0) ?? 0;
      return code <= 32 || code === 127;
    })
  )
    return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

// A source reference alone never grants permission to embed or copy a file.
export function approvedDelivery(media: {
  rights_status: string;
  delivery_url?: string | null;
}): string | null {
  if (media.rights_status !== "approved" || !media.delivery_url) return null;
  return MEDIA_ROUTE.test(media.delivery_url)
    ? media.delivery_url
    : safeSourceUrl(media.delivery_url);
}

export function playableMedia(media: {
  kind: string;
  mime_type: string;
  rights_status: string;
  delivery_url?: string | null;
}): "image" | "video" | null {
  if (!approvedDelivery(media)) return null;
  if (
    media.kind === "image" &&
    ["image/jpeg", "image/png", "image/webp", "image/avif"].includes(
      media.mime_type,
    )
  )
    return "image";
  if (
    media.kind === "video" &&
    ["video/mp4", "video/webm"].includes(media.mime_type)
  )
    return "video";
  return null;
}

type Handover = {
  precision: string;
  year: number;
  quarter?: number | null;
  month?: number | null;
  day?: number | null;
};

// Preserve source precision: a quarter is never converted into a delivery day.
export function formatHandover(
  handover: Handover,
  locale: string,
  quarterLabel: string,
): string | null {
  if (
    !Number.isInteger(handover.year) ||
    handover.year < 1900 ||
    handover.year > 2200
  )
    return null;
  const integer = new Intl.NumberFormat(locale, { useGrouping: false });
  const year = integer.format(handover.year);
  if (handover.precision === "year") return year;
  if (handover.precision === "quarter")
    return Number.isInteger(handover.quarter) &&
      handover.quarter != null &&
      handover.quarter >= 1 &&
      handover.quarter <= 4
      ? `${quarterLabel} ${integer.format(handover.quarter)} · ${year}`
      : null;
  if (
    !Number.isInteger(handover.month) ||
    !handover.month ||
    handover.month < 1 ||
    handover.month > 12
  )
    return null;
  if (handover.precision === "month")
    return new Intl.DateTimeFormat(locale, {
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(new Date(Date.UTC(handover.year, handover.month - 1, 1)));
  if (
    handover.precision !== "day" ||
    !Number.isInteger(handover.day) ||
    !handover.day
  )
    return null;
  const date = new Date(
    Date.UTC(handover.year, handover.month - 1, handover.day),
  );
  if (
    date.getUTCMonth() !== handover.month - 1 ||
    date.getUTCDate() !== handover.day
  )
    return null;
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "long",
    timeZone: "UTC",
  }).format(date);
}

type ProjectRelation = NonNullable<ProjectDetail["parent"]>;

// Same rule as isProjectSlug in data.ts; this module stays import-free for node tests.
const relationSlug = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** Reviewed component links render only with a routable slug and a safe source. */
export function projectRelations(
  project: Pick<ProjectDetail, "parent" | "components">,
) {
  const usable = (relation: ProjectRelation | null | undefined) =>
    relation && relation.slug.length <= 100 && relationSlug.test(relation.slug)
      ? { ...relation, source_url: safeSourceUrl(relation.source_url) }
      : null;
  return {
    parent: usable(project.parent),
    components: (project.components ?? []).flatMap((relation) => {
      const link = usable(relation);
      return link ? [link] : [];
    }),
  };
}
