import { NextResponse } from "next/server";
import { readPreview } from "@/features/atlas/server";

export async function GET(request: Request) {
  if (new URL(request.url).search)
    return NextResponse.json({ code: "invalid_query" }, { status: 400 });
  try {
    const result = await readPreview("imagery");
    return NextResponse.json(result.data ?? { code: "data_unavailable" }, {
      status: result.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ code: "data_unavailable" }, { status: 503 });
  }
}
