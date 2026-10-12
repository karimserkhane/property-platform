import { readPreview } from "@/features/atlas/server";

export async function GET(request: Request) {
  if (new URL(request.url).search)
    return Response.json({ code: "invalid_query" }, { status: 400 });
  try {
    const result = await readPreview("territories");
    return Response.json(result.data ?? { code: "data_unavailable" }, {
      status: result.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ code: "data_unavailable" }, { status: 503 });
  }
}
