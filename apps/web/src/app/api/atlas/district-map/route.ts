import { relayPreview, territorySearch } from "@/features/atlas/server";

export async function GET(request: Request) {
  if (territorySearch(request, []) === null)
    return Response.json({ code: "invalid_query" }, { status: 400 });
  return relayPreview(request, "district-map");
}
