import { relayPreview, territorySearch } from "@/features/atlas/server";

export async function GET(request: Request) {
  const search = territorySearch(request, ["bbox", "territory"]);
  if (search === null) {
    return Response.json({ code: "invalid_query" }, { status: 400 });
  }
  return relayPreview(request, "map-context", search);
}
