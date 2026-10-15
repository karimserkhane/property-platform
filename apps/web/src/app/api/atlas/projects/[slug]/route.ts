import { NextResponse } from "next/server";
import { territorySearch } from "@/features/atlas/server";
import { readProject } from "@/features/projects/server";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  if (territorySearch(request, []) === null)
    return NextResponse.json({ code: "invalid_query" }, { status: 400 });
  const { slug } = await params;
  const result = await readProject(slug);
  return NextResponse.json(result.project ?? { code: "data_unavailable" }, {
    status: result.status,
    headers: {
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
