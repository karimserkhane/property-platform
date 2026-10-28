type Bounds = readonly number[];

// This is a browser-restricted Embed API key, never a server API credential.
export function googleNeighbourhoodUrl(
  bounds: Bounds,
  locale: string,
  provider: string | undefined,
  browserKey: string | undefined,
) {
  if (
    provider !== "google" ||
    !browserKey ||
    !/^[\w-]{20,200}$/.test(browserKey)
  )
    return null;
  if (bounds.length !== 4 || !bounds.every(Number.isFinite)) return null;
  const [west, south, east, north] = bounds;
  if (
    west >= east ||
    south >= north ||
    west < -180 ||
    east > 180 ||
    south < -85 ||
    north > 85
  )
    return null;
  const span = Math.max(east - west, (north - south) * 1.5);
  const zoom = Math.max(1, Math.min(18, Math.floor(Math.log2(360 / span)) - 1));
  const url = new URL("https://www.google.com/maps/embed/v1/view");
  url.searchParams.set("key", browserKey);
  url.searchParams.set("center", `${(south + north) / 2},${(west + east) / 2}`);
  url.searchParams.set("zoom", String(zoom));
  url.searchParams.set("language", locale);
  url.searchParams.set("maptype", "roadmap");
  return url.href;
}
