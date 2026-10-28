import { relayPreview, territorySearch } from "@/features/atlas/server";

export async function GET(request: Request) {
  const input = new URL(request.url).searchParams;
  if (territorySearch(request, ["q", "limit", "territory"]) === null) {
    return Response.json({ code: "invalid_query" }, { status: 400 });
  }
  const params = new URLSearchParams();
  for (const key of ["q", "limit", "territory"]) {
    const value = input.get(key);
    if (value !== null) params.set(key, value);
  }
  return relayPreview(request, "parcel-search", `?${params}`);
}
