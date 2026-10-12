import { readPreview, territorySearch } from "@/features/atlas/server";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const search = territorySearch(request);
  if (search === null)
    return Response.json({ code: "invalid_query" }, { status: 400 });
  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
  ) {
    return Response.json({ code: "not_found" }, { status: 404 });
  }
  try {
    const result = await readPreview(`parcels/${id}`, search);
    return Response.json(result.data ?? { code: "data_unavailable" }, {
      status: result.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ code: "data_unavailable" }, { status: 503 });
  }
}
