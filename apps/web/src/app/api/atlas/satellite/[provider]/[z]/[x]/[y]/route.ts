// Public annual imagery only; no arbitrary URL, credentials or raster processing.
const YEARS: Record<string, { year: number; version: string }> = {
  openfreemap: { year: 0, version: "archive" },
  "sentinel-worldcover-2020": { year: 2020, version: "v1" },
  "sentinel-worldcover-2021": { year: 2021, version: "v2" },
};
const MAX_BYTES = 4 * 1024 * 1024;
const error = (status: number, code: string) =>
  Response.json({ code }, { status, headers: { "Cache-Control": "no-store" } });

export async function GET(
  request: Request,
  context: {
    params: Promise<{ provider: string; z: string; x: string; y: string }>;
  },
) {
  const { provider, z, x, y } = await context.params;
  const source = Object.hasOwn(YEARS, provider) ? YEARS[provider] : null;
  if (!source) return error(404, "not_found");
  if (
    new URL(request.url).search ||
    ![z, x, y].every((value) => /^(0|[1-9]\d{0,4})$/.test(value)) ||
    Number(z) < (provider === "openfreemap" ? 0 : 8) ||
    Number(z) > 14 ||
    Number(x) >= 2 ** Number(z) ||
    Number(y) >= 2 ** Number(z)
  )
    return error(400, "invalid_query");
  if (
    process.env.NODE_ENV === "production" &&
    process.env.PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW !== "1"
  )
    return error(403, "preview_disabled");

  const url = new URL(
    `/api/v1/preview/basemap/${provider}/${z}/${x}/${y}`,
    process.env.PROPERTY_PLATFORM_API_ORIGIN ?? "http://127.0.0.1:8000",
  );
  const mime =
    provider === "openfreemap" ? "application/x-protobuf" : "image/png";
  try {
    const upstream = await fetch(url, {
      headers: { Accept: mime },
      redirect: "error",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(20000)]),
      cache: "no-store",
    });
    if (upstream.status === 202)
      return new Response(null, {
        status: 202,
        headers: { "Cache-Control": "no-store", "Retry-After": "3" },
      });
    const length = upstream.headers.get("content-length");
    if (
      !upstream.ok ||
      !upstream.body ||
      upstream.headers.get("content-type")?.split(";")[0] !== mime ||
      (length !== null && (!/^\d+$/.test(length) || Number(length) > MAX_BYTES))
    ) {
      await upstream.body?.cancel();
      return error(503, "imagery_unavailable");
    }
    const reader = upstream.body.getReader();
    const chunks: Uint8Array[] = [];
    let total = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_BYTES) {
        await reader.cancel();
        return error(503, "imagery_unavailable");
      }
      chunks.push(value);
    }
    const image = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      image.set(chunk, offset);
      offset += chunk.byteLength;
    }
    const view = new DataView(image.buffer);
    if (
      (length !== null && total !== Number(length)) ||
      (provider !== "openfreemap" &&
        (total < 33 ||
          ![137, 80, 78, 71, 13, 10, 26, 10].every(
            (byte, i) => image[i] === byte,
          ) ||
          view.getUint32(12) !== 0x49484452 ||
          view.getUint32(16) !== 256 ||
          view.getUint32(20) !== 256)) ||
      (provider === "openfreemap" && total > 0 && image[0] !== 0x1a)
    )
      return error(503, "imagery_unavailable");
    return new Response(image, {
      headers: {
        "Content-Type": mime,
        "Cache-Control": "public, max-age=86400, s-maxage=604800",
        "X-Imagery-Source": provider,
        "X-Imagery-Period": String(source.year),
        "X-Source-Retrieved-At":
          upstream.headers.get("X-Source-Retrieved-At") ?? "",
        "X-Source-Ingested-At":
          upstream.headers.get("X-Source-Ingested-At") ?? "",
      },
    });
  } catch {
    return error(503, "imagery_unavailable");
  }
}
