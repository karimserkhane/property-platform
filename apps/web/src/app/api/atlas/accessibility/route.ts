import { NextResponse } from "next/server";
import { readPreview, territorySearch } from "@/features/atlas/server";

export async function GET(request: Request) {
  const search = territorySearch(request, [
    "territory",
    "longitude",
    "latitude",
    "minutes",
  ]);
  if (search === null)
    return NextResponse.json({ code: "invalid_query" }, { status: 400 });
  try {
    const result = await readPreview("accessibility", search);
    return NextResponse.json(result.data ?? { code: "data_unavailable" }, {
      status: result.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ code: "data_unavailable" }, { status: 503 });
  }
}
