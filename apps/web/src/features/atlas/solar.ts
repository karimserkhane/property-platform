import { convex } from "@turf/convex";
import { destination } from "@turf/destination";
import type { Feature, FeatureCollection, Point, Polygon } from "geojson";
import type { LightSpecification } from "maplibre-gl";
import { getPosition, getTimes } from "suncalc";
import type { MapFeature } from "./types";

export function dubaiClock(now = new Date()) {
  return new Date(now.valueOf() + 4 * 3600000).toISOString().slice(0, 16);
}
export function solarInstant(local: string): Date | null {
  if (!/^20\d{2}-\d\d-\d\dT\d\d:\d\d$/.test(local)) return null;
  const instant = new Date(`${local}:00+04:00`);
  if (!Number.isFinite(instant.valueOf()) || dubaiClock(instant) !== local)
    return null;
  return instant;
}
export function sunlight(local: string, longitude: number, latitude: number) {
  const instant = solarInstant(local);
  if (
    !instant ||
    !Number.isFinite(longitude) ||
    !Number.isFinite(latitude) ||
    Math.abs(longitude) > 180 ||
    Math.abs(latitude) > 85
  )
    return null;
  const position = getPosition(instant, latitude, longitude);
  const times = getTimes(instant, latitude, longitude, 0, 240);
  const daylight = position.altitude > 0;
  const elevation = Math.max(0, Math.sin((position.altitude * Math.PI) / 180));
  // Display lighting only, not irradiance, weather, indoor illuminance or lux.
  const light: LightSpecification = {
    anchor: "map",
    position: [
      1.5,
      position.azimuth,
      Math.min(180, Math.max(0, 90 - position.altitude)),
    ],
    color: daylight && position.altitude < 12 ? "#ffd3a0" : "#ffffff",
    intensity: daylight ? 0.2 + elevation * 0.65 : 0.05,
    "intensity-transition": { duration: 0 },
    "position-transition": { duration: 0 },
    "color-transition": { duration: 0 },
  };
  return {
    ...position,
    daylight,
    elevation,
    light,
    sunrise: times.sunrise,
    sunset: times.sunset,
  };
}

export function shadowPolygons(
  buildings: MapFeature[],
  local: string,
  longitude: number,
  latitude: number,
): FeatureCollection<Polygon> {
  const sun = sunlight(local, longitude, latitude);
  const features: Feature<Polygon>[] = [];
  // Very low sunlight produces arbitrarily long shadows and unstable flat-plane estimates.
  if (!sun || sun.altitude < 5) return { type: "FeatureCollection", features };
  let vertices = 0;
  for (const building of buildings.slice(0, 300)) {
    const height = building.properties.height_m;
    if (
      !height ||
      height <= 0 ||
      height > 1200 ||
      building.geometry.type !== "MultiPolygon"
    )
      continue;
    const polygons = building.geometry.coordinates as number[][][][];
    const ring = polygons.flatMap((rings) => rings[0] ?? []);
    if (ring.length > 500 || vertices + ring.length > 10000) continue;
    vertices += ring.length;
    const shadowLength = Math.min(
      3000,
      height / Math.tan((sun.altitude * Math.PI) / 180),
    );
    const points: Feature<Point>[] = ring.flatMap((coordinate) => {
      const displaced = destination(
        coordinate,
        shadowLength,
        sun.azimuth + 180,
        { units: "meters" },
      );
      return [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: coordinate },
          properties: {},
        },
        displaced,
      ];
    });
    const hull = convex({ type: "FeatureCollection", features: points });
    if (hull)
      features.push({
        ...hull,
        properties: { id: building.id, height_m: height },
      });
  }
  return { type: "FeatureCollection", features };
}
