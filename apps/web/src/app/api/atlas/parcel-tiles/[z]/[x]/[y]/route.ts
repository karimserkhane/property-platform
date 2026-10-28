import { relayVectorTile } from "@/features/atlas/vector-tile-route";

// Parcel footprints by identity only; attributes come from `parcel-index`.
export async function GET(
  request: Request,
  context: { params: Promise<{ z: string; x: string; y: string }> },
) {
  return relayVectorTile(
    request,
    "parcel-tiles",
    { min: 8, max: 16 },
    await context.params,
  );
}
