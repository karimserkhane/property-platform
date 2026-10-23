import "server-only";
import { jsonResponse } from "./json-response";

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
  const result = await readPreviewBytes(path, search, "application/json");
  return {
    status: result.status,
    data:
      result.bytes === null
        ? null
        : (JSON.parse(result.bytes.toString("utf8")) as unknown),
  };
}

// Bounded upstream body; null bytes for a disabled preview, an error or a 304.
export async function readPreviewBytes(
  path: string,
  search: string,
  accept: string,
  ifNoneMatch: string | null = null,
) {
  if (
    process.env.NODE_ENV === "production" &&
    process.env.PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW !== "1"
  ) {
    return { status: 403, bytes: null, contentType: null, etag: null };
  }
  const origin =
    process.env.PROPERTY_PLATFORM_API_ORIGIN ?? "http://127.0.0.1:8000";
  const response = await fetch(
    new URL(`/api/v1/preview/${path}${search}`, origin),
    {
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
      redirect: "error",
      headers: {
        Accept: accept,
        // Only the API's own validators are useful; anything longer is not one.
        ...(ifNoneMatch && ifNoneMatch.length <= 256
          ? { "If-None-Match": ifNoneMatch }
          : {}),
      },
    },
  );
  const contentType = response.headers.get("content-type");
  const etag = response.headers.get("etag");
  if (!response.ok || !response.body)
    return { status: response.status, bytes: null, contentType, etag };
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
  return {
    status: response.status,
    bytes: Buffer.concat(chunks),
    contentType,
    etag,
  };
}

// The API validates its reads against the data version; the browser may keep a
// copy but must revalidate it. Without a validator nothing is stored.
export function validatorHeaders(etag: string | null): HeadersInit {
  return etag
    ? { ETag: etag, "Cache-Control": "private, no-cache" }
    : { "Cache-Control": "no-store" };
}

// Shared relay answer: upstream status and validator, encoded JSON.
export async function relayPreview(
  request: Request,
  path: string,
  search = "",
) {
  try {
    const result = await readPreviewBytes(
      path,
      search,
      "application/json",
      request.headers.get("if-none-match"),
    );
    if (result.status === 304)
      return new Response(null, {
        status: 304,
        headers: validatorHeaders(result.etag),
      });
    const data =
      result.bytes === null
        ? null
        : (JSON.parse(result.bytes.toString("utf8")) as unknown);
    return await jsonResponse(request, data ?? { code: "data_unavailable" }, {
      status: result.status,
      headers: validatorHeaders(result.status === 200 ? result.etag : null),
    });
  } catch {
    return Response.json({ code: "data_unavailable" }, { status: 503 });
  }
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
