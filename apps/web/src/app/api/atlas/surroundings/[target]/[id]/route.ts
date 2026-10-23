import { relayPreview, territorySearch } from "@/features/atlas/server";

export async function GET(
  request: Request,
  {
    params,
  }: {
    params: Promise<{ target: string; id: string }>;
  },
) {
  const { target, id } = await params;
  const search = territorySearch(request);
  if (search === null)
    return Response.json({ code: "invalid_query" }, { status: 400 });
  if (
    !["parcel", "building", "place", "street"].includes(target) ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
  )
    return Response.json({ code: "not_found" }, { status: 404 });
  return relayPreview(request, `surroundings/${target}/${id}`, search);
}
