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
