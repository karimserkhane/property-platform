import type { MapContext, MapFeature } from "../atlas/types";

type ProjectMapPoint = MapFeature & {
  geometry: { type: "Point"; coordinates: [number, number] };
};

// A project name or a nearby parcel is never sufficient to locate a project.
export function projectMapPoints(
  data: MapContext,
  slug: string,
  bounds: readonly number[],
): ProjectMapPoint[] {
  const [west, south, east, north] = bounds;
  return data.place.features.filter((feature): feature is ProjectMapPoint => {
    if (
      feature.geometry.type !== "Point" ||
      feature.geometry.coordinates.length !== 2 ||
      feature.properties.presentation?.project?.slug !== slug
    )
      return false;
    const [lng, lat] = feature.geometry.coordinates;
    return (
      typeof lng === "number" &&
      typeof lat === "number" &&
      Number.isFinite(lng) &&
      Number.isFinite(lat) &&
      lng >= west &&
      lng <= east &&
      lat >= south &&
      lat <= north
    );
  });
}

export function projectPointBounds(
  points: ProjectMapPoint[],
): [[number, number], [number, number]] | null {
  const coordinates = points.map((point) => point.geometry.coordinates);
  if (!coordinates.length) return null;
  return [
    [
      Math.min(...coordinates.map(([lng]) => lng)),
      Math.min(...coordinates.map(([, lat]) => lat)),
    ],
    [
      Math.max(...coordinates.map(([lng]) => lng)),
      Math.max(...coordinates.map(([, lat]) => lat)),
    ],
  ];
}
