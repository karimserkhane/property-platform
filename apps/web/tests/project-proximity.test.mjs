import assert from "node:assert/strict";
import test from "node:test";
import {
  nearbyProject,
  parcelPropertyIndex,
  pointParcelDistance,
  preferredParcelProperty,
} from "../src/features/atlas/presentation.ts";
import { projectPulseFrame } from "../src/features/atlas/project-pulse.ts";

const ring = (x, y, w) => [
  [x, y],
  [x + w, y],
  [x + w, y + w],
  [x, y + w],
  [x, y],
];
const geometry = {
  type: "MultiPolygon",
  coordinates: [[ring(54.4, 24.5, 0.001), ring(54.4004, 24.5004, 0.0002)]],
};
const project = (id, x, y, name = id) => ({
  id,
  geometry: { type: "Point", coordinates: [x, y] },
  properties: {
    id,
    name,
    name_ar: "",
    kind: "publisher_project_marker",
    parcel_ids: [],
    source: { url: `https://example.com/${id}` },
  },
});
const parcel = (id, category = "residential") => ({
  id,
  geometry,
  properties: { category },
});

test("distance measures the actual footprint, retaining holes and disconnected parts", () => {
  assert.equal(pointParcelDistance(geometry, [54.4001, 24.5001]), 0);
  assert.equal(pointParcelDistance(geometry, [54.4, 24.5]), 0);
  assert.ok(pointParcelDistance(geometry, [54.4005, 24.5005]) > 9);
  const outside = pointParcelDistance(geometry, [54.4012, 24.5005]);
  assert.ok(outside > 19 && outside < 21);
  const parts = {
    type: "MultiPolygon",
    coordinates: [...geometry.coordinates, [ring(54.403, 24.503, 0.001)]],
  };
  assert.equal(pointParcelDistance(parts, [54.4035, 24.5035]), 0);
  assert.ok(pointParcelDistance(parts, [54.402, 24.502]) > 100);
});

test("suggestions are bounded to 50 m and skip ambiguous distinct projects", () => {
  const near = project("near", 54.4012, 24.5005);
  const far = project("far", 54.4016, 24.5005);
  assert.equal(nearbyProject(geometry, [far]), null);
  assert.equal(nearbyProject(geometry, [far, near]).feature, near);
  const rival = project("rival", 54.40125, 24.5005);
  assert.equal(nearbyProject(geometry, [near, rival]), null);
  const same = project("same-observation", 54.4012, 24.5005, "near");
  assert.equal(nearbyProject(geometry, [same, near]), null);
  same.properties.presentation = { project: { slug: "same-project" } };
  near.properties.presentation = { project: { slug: "same-project" } };
  assert.equal(nearbyProject(geometry, [same, near]).feature, near);
  assert.equal(nearbyProject(geometry, [near, same]).feature, near);
});

test("inference preserves source geometry and identities, excluding public and named parcels", () => {
  const near = project("near", 54.4012, 24.5005);
  const known = project("known", 54.402, 24.502);
  known.properties.parcel_ids = ["known-parcel"];
  const context = {
    place: { features: [near, known] },
    building: { features: [] },
  };
  const data = {
    features: [
      parcel("new"),
      parcel("school", "public"),
      parcel("overlay", "overlay"),
      parcel("known-parcel"),
    ],
  };
  const before = JSON.stringify({ context, data });
  const index = parcelPropertyIndex(context, data);
  const suggestion = preferredParcelProperty(index.get("new"), "en");
  assert.equal(suggestion.feature, near);
  assert.equal(suggestion.spatial_match.method, "boundary-proximity-v1");
  assert.equal(suggestion.spatial_match.source_feature_id, "near");
  assert.ok(suggestion.spatial_match.distance_m < 50);
  assert.equal(index.has("school"), false);
  assert.equal(index.has("overlay"), false);
  assert.equal(
    preferredParcelProperty(index.get("known-parcel"), "en").id,
    "known",
  );
  assert.equal(
    preferredParcelProperty(
      [suggestion, { ...known.properties, id: "known", feature: known }],
      "en",
    ).id,
    "known",
  );
  assert.equal(JSON.stringify({ context, data }), before);
  assert.deepEqual(parcelPropertyIndex(context, data), index);
});

test("project halos cycle slowly within bounded size and opacity", () => {
  for (const time of [0, 60, 600, 1200, 2399, 2400, 100000]) {
    const f = projectPulseFrame(time);
    assert.ok(f.radius >= 10 && f.radius <= 25);
    assert.ok(f.opacity >= 0 && f.opacity <= 0.24);
  }
  assert.deepEqual(projectPulseFrame(0), projectPulseFrame(2400));
  assert.ok(projectPulseFrame(1200).radius > projectPulseFrame(0).radius);
  assert.ok(projectPulseFrame(1200).opacity < projectPulseFrame(0).opacity);
});
