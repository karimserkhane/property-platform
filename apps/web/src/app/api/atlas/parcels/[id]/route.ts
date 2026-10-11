import { readPreview } from "@/features/atlas/server";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
  ) {
    return Response.json({ code: "not_found" }, { status: 404 });
  }
  try {
    const result = await readPreview(`parcels/${id}`);
    return Response.json(result.data ?? { code: "data_unavailable" }, {
      status: result.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ code: "data_unavailable" }, { status: 503 });
  }
}
