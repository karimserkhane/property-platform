import { NextResponse } from "next/server";
import { readPropertyMedia, territorySearch } from "@/features/atlas/server";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
  )
    return NextResponse.json({ code: "not_found" }, { status: 404 });
  if (territorySearch(request, []) === null)
    return NextResponse.json({ code: "invalid_query" }, { status: 400 });
  try {
    const media = await readPropertyMedia(id);
    if (!media.bytes)
      return NextResponse.json(
        { code: "data_unavailable" },
        { status: media.status },
      );
    return new Response(new Uint8Array(media.bytes), {
      headers: {
        "Content-Type": media.mime,
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return NextResponse.json({ code: "data_unavailable" }, { status: 503 });
  }
}
