import { readPreview, territorySearch } from "@/features/atlas/server";

export async function GET(request: Request) {
  const input = new URL(request.url).searchParams;
  if (territorySearch(request, ["bbox", "q", "limit", "territory"]) === null) {
    return Response.json({ code: "invalid_query" }, { status: 400 });
  }
  const params = new URLSearchParams();
  for (const key of ["bbox", "q", "limit", "territory"]) {
    const value = input.get(key);
    if (value !== null) params.set(key, value);
  }
  try {
    const result = await readPreview("parcels", `?${params}`);
    return Response.json(result.data ?? { code: "data_unavailable" }, {
      status: result.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ code: "data_unavailable" }, { status: 503 });
  }
}
