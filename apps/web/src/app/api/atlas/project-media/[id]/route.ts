// Fixed private upstream. Forward a bounded stream, never an arbitrary remote URL.
const MAX_BYTES = 128 * 1024 * 1024;
const MIMES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
  "video/mp4",
  "video/webm",
  "model/gltf-binary",
]);
const error = (status: number, code = "data_unavailable") =>
  Response.json({ code }, { status, headers: { "Cache-Control": "no-store" } });

async function relay(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
  )
    return error(404, "not_found");
  if (new URL(request.url).search) return error(400, "invalid_query");
  if (
    process.env.NODE_ENV === "production" &&
    process.env.PROPERTY_PLATFORM_ENABLE_LOCAL_PREVIEW !== "1"
  )
    return error(403, "preview_disabled");
  const headers = new Headers();
  for (const name of ["Range", "If-Range"]) {
    const value = request.headers.get(name);
    if (value && value.length > 100) return error(400, "invalid_query");
    if (value) headers.set(name, value);
  }
  const controller = new AbortController();
  const abort = () => controller.abort();
  request.signal.addEventListener("abort", abort, { once: true });
  const timer = setTimeout(abort, 10000);
  const cleanup = () => {
    clearTimeout(timer);
    request.signal.removeEventListener("abort", abort);
  };
  try {
    const upstream = await fetch(
      new URL(
        `/api/v1/preview/project-media/${id}`,
        process.env.PROPERTY_PLATFORM_API_ORIGIN ?? "http://127.0.0.1:8000",
      ),
      {
        method: request.method,
        headers,
        signal: controller.signal,
        cache: "no-store",
        redirect: "error",
      },
    );
    clearTimeout(timer);
    if (upstream.status === 416) {
      await upstream.body?.cancel();
      cleanup();
      const contentRange = upstream.headers.get("content-range") ?? "";
      if (
        !/^bytes \*\/\d+$/.test(contentRange) ||
        Number(contentRange.split("/")[1]) > MAX_BYTES
      )
        return error(503);
      return new Response(null, {
        status: 416,
        headers: { "Content-Range": contentRange, "Cache-Control": "no-store" },
      });
    }
    if (![200, 206].includes(upstream.status)) {
      await upstream.body?.cancel();
      cleanup();
      return error(
        [403, 404].includes(upstream.status) ? upstream.status : 503,
      );
    }
    const length = Number(upstream.headers.get("content-length"));
    const mime = upstream.headers.get("content-type") ?? "";
    if (
      !Number.isSafeInteger(length) ||
      length < 1 ||
      length > MAX_BYTES ||
      !MIMES.has(mime)
    )
      throw new Error("Invalid media metadata");
    if (upstream.status === 206) {
      const span = /^bytes (\d+)-(\d+)\/(\d+)$/.exec(
        upstream.headers.get("content-range") ?? "",
      );
      if (
        !span ||
        Number(span[3]) > MAX_BYTES ||
        Number(span[2]) >= Number(span[3]) ||
        Number(span[2]) - Number(span[1]) + 1 !== length
      )
        throw new Error("Invalid byte range");
    }
    const responseHeaders = new Headers({
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    });
    for (const name of [
      "Content-Type",
      "Content-Length",
      "Content-Range",
      "Accept-Ranges",
      "ETag",
      "Content-Disposition",
    ]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    if (request.method === "HEAD") {
      await upstream.body?.cancel();
      cleanup();
      return new Response(null, { headers: responseHeaders });
    }
    if (!upstream.body) throw new Error("Missing media stream");
    const reader = upstream.body.getReader();
    let count = 0;
    const body = new ReadableStream<Uint8Array>({
      async pull(stream) {
        const idleTimer = setTimeout(abort, 30000);
        try {
          const { done, value } = await reader.read();
          if (done) {
            if (count !== length) throw new Error("Incomplete media");
            cleanup();
            stream.close();
            return;
          }
          count += value.byteLength;
          if (count > length) throw new Error("Media exceeds budget");
          stream.enqueue(value);
        } catch {
          controller.abort();
          await reader.cancel().catch(() => {});
          cleanup();
          stream.error(new Error("Media unavailable"));
        } finally {
          clearTimeout(idleTimer);
        }
      },
      async cancel() {
        controller.abort();
        cleanup();
        await reader.cancel().catch(() => {});
      },
    });
    return new Response(body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    controller.abort();
    cleanup();
    return error(503);
  }
}

export const GET = relay;
export const HEAD = relay;
