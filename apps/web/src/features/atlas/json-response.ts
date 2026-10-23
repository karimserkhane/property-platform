import { promisify } from "node:util";
import { brotliCompress, constants, gzip } from "node:zlib";

const brotli = promisify(brotliCompress);
const gzipped = promisify(gzip);

// Below this size the encoding overhead outweighs the transfer it saves.
const MIN_ENCODED_BYTES = 1024;
// Quality 5 keeps a 1.5 MB map payload within a few tens of milliseconds.
const BROTLI_OPTIONS = {
  params: {
    [constants.BROTLI_PARAM_QUALITY]: 5,
    [constants.BROTLI_PARAM_MODE]: constants.BROTLI_MODE_TEXT,
  },
};

export type JsonEncoding = "br" | "gzip";

export function acceptedEncoding(header: string | null): JsonEncoding | null {
  const weights = new Map<string, number>();
  for (const part of (header ?? "").split(",")) {
    const [name, ...params] = part.trim().toLowerCase().split(";");
    if (!name) continue;
    const q = params
      .map((param) => param.trim())
      .find((p) => p.startsWith("q="));
    const weight = q === undefined ? 1 : Number(q.slice(2));
    weights.set(name, Number.isFinite(weight) ? weight : 0);
  }
  const weight = (name: string) => weights.get(name) ?? weights.get("*") ?? 0;
  if (weight("br") > 0 && weight("br") >= weight("gzip")) return "br";
  return weight("gzip") > 0 ? "gzip" : null;
}

// Next.js compresses rendered pages but not route handler bodies, so the
// relays encode their JSON here. Payload contents are never altered.
export function jsonResponse(
  request: Request,
  body: unknown,
  init: ResponseInit = {},
) {
  return encodedResponse(
    request,
    Buffer.from(JSON.stringify(body)),
    "application/json",
    init,
  );
}

// Same encoding for compressible binary relays such as vector tiles.
export async function encodedResponse(
  request: Request,
  body: Uint8Array,
  contentType: string,
  init: ResponseInit = {},
) {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", contentType);
  headers.append("Vary", "Accept-Encoding");
  const encoding =
    body.byteLength >= MIN_ENCODED_BYTES
      ? acceptedEncoding(request.headers.get("accept-encoding"))
      : null;
  if (encoding === null)
    return new Response(new Uint8Array(body), { ...init, headers });
  const bytes =
    encoding === "br"
      ? await brotli(body, BROTLI_OPTIONS)
      : await gzipped(body);
  headers.set("Content-Encoding", encoding);
  return new Response(new Uint8Array(bytes), { ...init, headers });
}
