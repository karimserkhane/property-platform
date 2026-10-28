import { relayVectorTile } from "@/features/atlas/vector-tile-route";

// Building and street footprints; attributes come from `context-index`.
export async function GET(
  request: Request,
  context: { params: Promise<{ z: string; x: string; y: string }> },
) {
  return relayVectorTile(
    request,
    "context-tiles",
    { min: 11, max: 16 },
    await context.params,
  );
}
