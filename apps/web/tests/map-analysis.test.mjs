import assert from "node:assert/strict";
import test from "node:test";
import {
  clusteredProjects,
  measurement,
  projectsInZone,
  searchItems,
  searchMap,
  withParcelMatches,
} from "../src/features/atlas/map-analysis.ts";
import { selectMapHit } from "../src/features/atlas/presentation.ts";
import {
  dubaiClock,
  shadowPolygons,
  solarInstant,
  sunlight,
} from "../src/features/atlas/solar.ts";

const feature = (id, name, coordinates, slug = null) => ({
  type: "Feature",
  id,
  geometry: { type: "Point", coordinates },
  properties: {
    name,
    name_ar: "جزيرة الريم",
    kind: slug ? "catalogue_project_marker" : "shop",
    source: { url: `https://example.com/${id}` },
    presentation: slug ? { project: { slug }, display_name: name } : null,
  },
});
const context = {
  place: {
    features: [
      feature("a", "Émeraude", [54.4, 24.5], "emerald"),
      feature("b", "Second entrance", [54.401, 24.5], "emerald"),
      feature("c", "Outside", [54.6, 24.6], "outside"),
      feature("d", "Emerald Café", [54.4, 24.5]),
    ],
  },
  building: { features: [] },
  street: { features: [] },
  administrative_area: { features: [] },
};

test("clusters count canonical projects, without counting entrances or shops twice", () => {
  const result = clusteredProjects(context);
  assert.deepEqual(
    result.features.map((f) => f.id),
    ["a", "c"],
  );
  assert.equal(context.place.features.length, 4);
});
test("project circles retain selection priority when their name label is hidden", () => {
  const building = { properties: { id: "tower" }, layer: { id: "buildings" } };
  const parcel = { properties: { id: "plot" }, layer: { id: "parcel-fill" } };
  for (const layer of ["single-project", "close-project"]) {
    const project = {
      properties: { id: "project", kind: "publisher_project_marker" },
      layer: { id: layer },
    };
    assert.equal(selectMapHit([parcel, building, project]), project);
    assert.equal(selectMapHit([project]), project);
  }
});
test("search handles accents and Arabic, prioritises projects and keeps parcel identity", () => {
  const parcels = {
    features: [
      {
        id: "parcel-id",
        geometry: { type: "MultiPolygon", coordinates: [] },
        properties: { code: "P-123" },
      },
    ],
  };
  const items = searchItems(context, parcels, "fr");
  assert.equal(searchMap(items, "emeraude")[0].key, "project:emerald");
  assert.equal(searchMap(items, "الريم").length, 3);
  assert.equal(searchMap(items, "p-123")[0].parcelId, "parcel-id");
  assert.deepEqual(searchMap(items, "e"), []);
});
test("distance uses geodesic metres; zones have area and list unique contained projects", () => {
  const straight = measurement(
    [
      [54.4, 24.5],
      [54.401, 24.5],
    ],
    false,
  );
  assert.ok(straight.metres > 100 && straight.metres < 102);
  assert.equal(straight.polygon, null);
  const zone = measurement(
    [
      [54.39, 24.49],
      [54.41, 24.49],
      [54.41, 24.51],
      [54.39, 24.51],
    ],
    true,
  );
  assert.ok(zone.squareMetres > 4e6 && zone.squareMetres < 5e6);
  assert.deepEqual(
    projectsInZone(searchItems(context, null, "en"), zone.polygon).map(
      (i) => i.key,
    ),
    ["project:emerald"],
  );
  assert.equal(measurement([[54.4, 24.5]], true).polygon, null);
});
test("solar inputs always mean Dubai civil time, including invalid calendar rejection", () => {
  assert.equal(
    solarInstant("2026-10-20T12:00").toISOString(),
    "2026-10-20T08:00:00.000Z",
  );
  assert.equal(
    dubaiClock(new Date("2026-10-19T22:30:00Z")),
    "2026-10-20T02:30",
  );
  for (const value of [
    "2026-02-30T12:00",
    "2026-10-20T25:00",
    "2026-10-20T12:00Z",
    "1999-10-20T12:00",
    "",
  ])
    assert.equal(solarInstant(value), null);
});
test("sun uses degrees north clockwise and a stable map anchored light", () => {
  const morning = sunlight("2026-10-20T08:00", 54.4, 24.5);
  const noon = sunlight("2026-10-20T12:00", 54.4, 24.5);
  const night = sunlight("2026-10-20T00:00", 54.4, 24.5);
  assert.ok(morning.azimuth > 90 && morning.azimuth < 135);
  assert.ok(noon.altitude > 50 && noon.altitude < 60);
  assert.ok(noon.altitude > morning.altitude);
  assert.ok(morning.daylight && !night.daylight);
  assert.equal(noon.light.anchor, "map");
  assert.equal(noon.light.position[1], noon.azimuth);
  assert.equal(noon.light.position[2], 90 - noon.altitude);
  assert.ok(dubaiClock(noon.sunrise).startsWith("2026-10-20T06:"));
  assert.equal(sunlight("2026-10-20T12:00", NaN, 24.5), null);
});
test("shadows require recorded heights and fall opposite the morning sun; none at night", () => {
  const building = {
    id: "tower",
    geometry: {
      type: "MultiPolygon",
      coordinates: [
        [
          [
            [54.4, 24.5],
            [54.4001, 24.5],
            [54.4001, 24.5001],
            [54.4, 24.5001],
            [54.4, 24.5],
          ],
        ],
      ],
    },
    properties: { height_m: 100 },
  };
  const result = shadowPolygons(
    [building, { ...building, properties: { levels: 30 } }],
    "2026-10-20T08:00",
    54.4,
    24.5,
  );
  assert.equal(result.features.length, 1);
  const coordinates = result.features[0].geometry.coordinates[0];
  assert.ok(Math.min(...coordinates.map((c) => c[0])) < 54.399);
  assert.equal(
    shadowPolygons([building], "2026-10-20T00:00", 54.4, 24.5).features.length,
    0,
  );
  assert.equal(building.properties.height_m, 100);
});
test("server parcel matches fill free search slots after visible results without duplicates", () => {
  const row = (id, code) => ({
    id,
    properties: { code, bounds: [54.4, 24.5, 54.41, 24.51] },
  });
  const visible = searchItems(context, { features: [row("a", "P-1")] }, "en");
  const results = searchMap(visible, "p-");
  const merged = withParcelMatches(results, {
    features: [row("a", "P-1"), row("b", "P-2")],
  });
  assert.deepEqual(
    merged.map((item) => item.key),
    ["parcel:a", "parcel:b"],
  );
  assert.equal(merged[1].parcelId, "b");
  assert.equal(merged[1].geometry.type, "Polygon");
  const many = Array.from({ length: 20 }, (_, i) => row(`r${i}`, `P-${i}`));
  assert.equal(withParcelMatches([], { features: many }).length, 12);
  assert.deepEqual(withParcelMatches(results, null), results);
});
