import "server-only";

const MAX_BYTES = 8 * 1024 * 1024;

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
