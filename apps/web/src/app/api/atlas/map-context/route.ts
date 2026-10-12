import { NextResponse } from "next/server";
import { readPreview } from "@/features/atlas/server";

export async function GET(request: Request) {
  const url = new URL(request.url);
  if (
    url.search.length > 1000 ||
    [...url.searchParams.keys()].some((key) => key !== "bbox")
  ) {
    return NextResponse.json({ code: "invalid_query" }, { status: 400 });
  }
  try {
    const result = await readPreview("map-context", url.search);
    return NextResponse.json(result.data ?? { code: "data_unavailable" }, {
      status: result.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ code: "data_unavailable" }, { status: 503 });
  }
}
