import type { ProjectMapLocation } from "./types";

export function projectLocationBounds(
  locations: ProjectMapLocation[],
  bounds: readonly number[],
): [[number, number], [number, number]] | null {
  const [west, south, east, north] = bounds;
  const coordinates = locations.flatMap((location) =>
    location.geometry.coordinates.flat(Infinity),
  ) as number[];
  if (!coordinates.length || coordinates.length % 2 !== 0) return null;
  let left = east,
    bottom = north,
    right = west,
    top = south;
  for (let i = 0; i < coordinates.length; i += 2) {
    const lng = coordinates[i],
      lat = coordinates[i + 1];
    if (
      !Number.isFinite(lng) ||
      !Number.isFinite(lat) ||
      lng < west ||
      lng > east ||
      lat < south ||
      lat > north
    )
      return null;
    left = Math.min(left, lng);
    right = Math.max(right, lng);
    bottom = Math.min(bottom, lat);
    top = Math.max(top, lat);
  }
  return [
    [left, bottom],
    [right, top],
  ];
}

export function neighbourhoodContextBounds(
  focus: [[number, number], [number, number]] | null,
  area: readonly number[],
): number[] {
  if (!focus) return [...area];
  // Load the surroundings once; keep the requested area bounded to the same island.
  const margin = 0.008;
  return [
    Math.max(area[0], focus[0][0] - margin),
    Math.max(area[1], focus[0][1] - margin),
    Math.min(area[2], focus[1][0] + margin),
    Math.min(area[3], focus[1][1] + margin),
  ];
}
