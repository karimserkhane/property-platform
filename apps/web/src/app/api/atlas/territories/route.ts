import { relayPreview } from "@/features/atlas/server";

export async function GET(request: Request) {
  if (new URL(request.url).search)
    return Response.json({ code: "invalid_query" }, { status: 400 });
  return relayPreview(request, "territories");
}
