import "server-only";

const MAX_BYTES = 8 * 1024 * 1024;

export function territorySearch(
  request: Request,
  allowed: string[] = ["territory"],
) {
  const url = new URL(request.url);
  if (
    url.search.length > 1000 ||
    [...url.searchParams.keys()].some((key) => !allowed.includes(key))
  )
    return null;
  const territory = url.searchParams.get("territory");
  if (territory !== null && !/^[a-z0-9-]{1,80}$/.test(territory)) return null;
  return url.search;
}

// Only server configuration chooses the upstream; visitor input is never a URL.
export async function readPreview(path: string, search = "") {
  if (
    process.env.NODE_ENV === "production" &&
    process.env.PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW !== "1"
  ) {
    return { status: 403, data: null };
  }
  const origin =
    process.env.PROPERTY_PLATFORM_API_ORIGIN ?? "http://127.0.0.1:8000";
  const response = await fetch(
    new URL(`/api/v1/preview/${path}${search}`, origin),
    {
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
      redirect: "error",
      headers: { Accept: "application/json" },
    },
  );
  if (!response.ok || !response.body)
    return { status: response.status, data: null };
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BYTES) throw new Error("Preview exceeds response budget");
      chunks.push(value);
    }
  } finally {
    await reader.cancel();
  }
  const bytes = Buffer.concat(chunks);
  return { status: 200, data: JSON.parse(bytes.toString("utf8")) as unknown };
}

// A fixed, licensed-media endpoint only; no visitor-selected remote image URL.
export async function readPropertyMedia(id: string) {
  if (
    process.env.NODE_ENV === "production" &&
    process.env.PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW !== "1"
  )
    return { status: 403, bytes: null, mime: "" };
  const origin =
    process.env.PROPERTY_PLATFORM_API_ORIGIN ?? "http://127.0.0.1:8000";
  const response = await fetch(
    new URL(`/api/v1/preview/property-media/${id}`, origin),
    {
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
      redirect: "error",
    },
  );
  if (!response.ok || !response.body)
    return { status: response.status, bytes: null, mime: "" };
  const mime = response.headers.get("content-type") ?? "";
  if (mime !== "image/jpeg") throw new Error("Unexpected property media type");
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 2 * 1024 * 1024)
        throw new Error("Property image exceeds budget");
      chunks.push(value);
    }
  } finally {
    await reader.cancel();
  }
  return { status: 200, bytes: Buffer.concat(chunks), mime };
}
