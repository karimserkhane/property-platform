import "server-only";
import { encodedResponse } from "./json-response";
import { readPreviewBytes, territorySearch, validatorHeaders } from "./server";

const MIME = "application/vnd.mapbox-vector-tile";
const error = (status: number, code: string) =>
  Response.json({ code }, { status, headers: { "Cache-Control": "no-store" } });

// Relays one MVT tile of a preview family (`parcel-tiles`, `context-tiles`)
// within the zooms the API serves; attributes come from the matching index.
export async function relayVectorTile(
  request: Request,
  family: string,
  zooms: { min: number; max: number },
  { z, x, y }: { z: string; x: string; y: string },
) {
  const search = territorySearch(request);
  if (
    search === null ||
    ![z, x, y].every((value) => /^(0|[1-9]\d{0,5})$/.test(value)) ||
    Number(z) < zooms.min ||
    Number(z) > zooms.max ||
    Number(x) >= 2 ** Number(z) ||
    Number(y) >= 2 ** Number(z)
  )
    return error(400, "invalid_query");
  try {
    const result = await readPreviewBytes(
      `${family}/${z}/${x}/${y}`,
      search,
      MIME,
      request.headers.get("if-none-match"),
    );
    if (result.status === 204 || result.status === 304)
      return new Response(null, {
        status: result.status,
        headers: validatorHeaders(result.etag),
      });
    // An MVT layer message starts with field 3 (0x1a); anything else is refused.
    if (
      result.bytes === null ||
      result.contentType?.split(";")[0] !== MIME ||
      result.bytes[0] !== 0x1a
    )
      return error(
        result.status >= 400 ? result.status : 503,
        "data_unavailable",
      );
    return await encodedResponse(request, result.bytes, MIME, {
      headers: validatorHeaders(result.etag),
    });
  } catch {
    return error(503, "data_unavailable");
  }
}
