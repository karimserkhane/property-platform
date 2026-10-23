import { encodedResponse } from "@/features/atlas/json-response";
import { readPreviewBytes, territorySearch } from "@/features/atlas/server";

const MIME = "application/vnd.mapbox-vector-tile";
const error = (status: number, code: string) =>
  Response.json({ code }, { status, headers: { "Cache-Control": "no-store" } });

// Parcel footprints by identity only; attributes come from `parcel-index`.
export async function GET(
  request: Request,
  context: { params: Promise<{ z: string; x: string; y: string }> },
) {
  const { z, x, y } = await context.params;
  const search = territorySearch(request);
  if (
    search === null ||
    ![z, x, y].every((value) => /^(0|[1-9]\d{0,5})$/.test(value)) ||
    Number(z) < 8 ||
    Number(z) > 16 ||
    Number(x) >= 2 ** Number(z) ||
    Number(y) >= 2 ** Number(z)
  )
    return error(400, "invalid_query");
  try {
    const result = await readPreviewBytes(
      `parcel-tiles/${z}/${x}/${y}`,
      search,
      MIME,
    );
    if (result.status === 204)
      return new Response(null, {
        status: 204,
        headers: { "Cache-Control": "no-store" },
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
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return error(503, "data_unavailable");
  }
}
