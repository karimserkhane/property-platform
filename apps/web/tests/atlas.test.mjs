import assert from "node:assert/strict";
import test from "node:test";
import {
  csv,
  geometryBounds,
  normalized,
  parcelPropertyIndex,
  preferredParcelProperty,
  propertyFeatures,
  propertyName,
  readableParcelCode,
  selectMapHit,
} from "../src/features/atlas/presentation.ts";

const hit = (layer, id, properties = {}) => ({
  layer: { id: layer },
  properties: { id, ...properties },
});

const candidate = (id, name, kind, extra = {}) => ({
  id,
  name,
  name_ar: "",
  kind,
  feature: null,
  ...extra,
});

test("a parcel leads with an uncertain project name, ahead of businesses and provider-only records", () => {
  const cafe = candidate("cafe", "Cafe", "cafe");
  const provider = candidate("provider", "", "publisher_project_marker", {
    presentation: { name: "", developer: "Developer", publisher: "Publisher" },
  });
  const project = candidate("project", "The District", "broker_project_marker");
  const candidates = [provider, cafe, project];
  assert.equal(preferredParcelProperty(candidates, "en"), project);
  assert.equal(propertyName(project, "en"), "The District");
  assert.deepEqual(candidates, [provider, cafe, project]);
  assert.equal(preferredParcelProperty([cafe], "en"), null);
  assert.equal(preferredParcelProperty([], "en"), null);
});

test("unknown property names fall back to a recorded developer, then publisher", () => {
  const unnamed = candidate("a", " ", "publisher_project_marker", {
    presentation: {
      name: "",
      developer: "Reportage Properties",
      publisher: "Publisher",
    },
  });
  assert.equal(preferredParcelProperty([unnamed], "en"), unnamed);
  assert.equal(propertyName(unnamed, "en"), "Reportage Properties");
  assert.equal(
    propertyName(
      {
        ...unnamed,
        presentation: { name: "", developer: "", publisher: "Publisher" },
      },
      "en",
    ),
    "Publisher",
  );
  assert.equal(propertyName(candidate("none", "", "apartments"), "en"), "");
});

test("display names use Arabic when present and retain original names otherwise", () => {
  const p = candidate("a", "Source name", "apartments", {
    name_ar: "اسم المبنى",
    presentation: { name: "Reviewed name" },
  });
  assert.equal(propertyName(p, "ar"), "اسم المبنى");
  assert.equal(propertyName(p, "en"), "Reviewed name");
  assert.equal(propertyName({ ...p, name_ar: "" }, "ar"), "Reviewed name");
});

test("parcel headings enrich exact OSM point identities without merging equally named buildings", () => {
  const feature = (id, name, url, parcel_ids, geometry) => ({
    id,
    geometry: { type: geometry },
    properties: {
      id,
      name,
      name_ar: "",
      kind: "apartments",
      parcel_ids,
      source: { url },
    },
  });
  const building = feature(
    "building",
    "Tower",
    "https://www.openstreetmap.org/way/1",
    [],
    "MultiPolygon",
  );
  building.properties.presentation = { name: "Tower", developer: "Developer" };
  const point = feature(
    "point",
    "Tower",
    building.properties.source.url,
    ["parcel"],
    "Point",
  );
  const unrelated = feature(
    "other",
    "Tower",
    "https://www.openstreetmap.org/way/2",
    [],
    "MultiPolygon",
  );
  const context = {
    building: { features: [building, unrelated] },
    place: { features: [point] },
  };
  const index = parcelPropertyIndex(context);
  assert.equal(
    preferredParcelProperty(index.get("parcel"), "en").feature,
    building,
  );
  assert.equal(index.get("parcel").length, 1);
  assert.deepEqual(building.properties.parcel_ids, []);
  assert.deepEqual(point.properties.parcel_ids, ["parcel"]);
  assert.equal(parcelPropertyIndex(null).size, 0);
});

test("ambiguous names have a stable display preference without dropping alternative identities", () => {
  const a = candidate("a", "Alpha", "broker_project_marker");
  const b = candidate("b", "Beta", "publisher_project_marker");
  assert.equal(preferredParcelProperty([b, a], "en"), a);
  assert.equal(preferredParcelProperty([a, b], "en"), a);
});

test("cadastral references are readable without rewriting their original value", () => {
  const code = "RT3_C53_to_C56";
  assert.equal(readableParcelCode(code), "RT3 · C53–C56");
  assert.equal(readableParcelCode("RT4_C119"), "RT4 · C119");
  assert.equal(readableParcelCode("CUSTOM/X-7"), "CUSTOM/X-7");
  assert.equal(readableParcelCode(""), "");
  assert.equal(code, "RT3_C53_to_C56");
});

test("a building under the pointer wins over its parcel and sector", () => {
  const building = hit("buildings", "building");
  const parcel = hit("parcel-fill", "parcel", { category: "mixed" });
  const sector = hit("area-hit", "RT4", { kind: "community" });
  for (const hits of [
    [sector, parcel, building],
    [building, sector, parcel],
  ])
    assert.equal(selectMapHit(hits), building);
});

test("RT4 ProjectLimits never hides the real parcel under the pointer", () => {
  const overlay = hit("parcel-fill", "RT4_TMP_PL2", { category: "overlay" });
  const parcel = hit("parcel-fill", "RT4_C1", { category: "mixed" });
  const sector = hit("area-hit", "RT4", { kind: "community" });
  assert.equal(selectMapHit([overlay, sector, parcel]), parcel);
  assert.equal(selectMapHit([parcel, overlay, sector]), parcel);
  assert.equal(selectMapHit([overlay, sector]), null);
});

test("sectors, island and project perimeters are never click targets", () => {
  const district = hit("area-hit", "island", { kind: "district" });
  const sector = hit("area-hit", "RT4", { kind: "community" });
  const overlay = hit("parcel-fill", "RT4_TMP_PL2", { category: "overlay" });
  const place = hit("places", "place");
  const street = hit("streets", "street");
  assert.equal(selectMapHit([district, sector]), null);
  assert.equal(selectMapHit([district]), null);
  assert.equal(selectMapHit([district, overlay, street]), street);
  assert.equal(selectMapHit([overlay, street, place]), place);
  assert.equal(selectMapHit([]), null);
  assert.equal(selectMapHit([{ layer: { id: "buildings" } }]), null);
  assert.equal(selectMapHit([hit("unrelated-label", "unknown")]), null);
});

test("an explicit project marker opens its property rather than the underlying parcel", () => {
  const project = hit("places", "project", {
    kind: "publisher_project_marker",
  });
  const parcel = hit("parcel-fill", "parcel", { category: "mixed" });
  const building = hit("buildings", "building");
  assert.equal(selectMapHit([parcel, project]), project);
  assert.equal(selectMapHit([project, building, parcel]), building);
});

test("property discovery prioritizes documented records without inventing point-to-building links", () => {
  const basic = {
    id: "b",
    properties: { name: "Basic", name_ar: "", kind: "residential" },
  };
  const documented = {
    id: "a",
    properties: {
      name: "Documented",
      name_ar: "",
      kind: "yes",
      presentation: {},
    },
  };
  const project = {
    id: "p",
    properties: { name: "Project", name_ar: "", kind: "broker_project_marker" },
  };
  const cafe = {
    id: "c",
    properties: { name: "Cafe", name_ar: "", kind: "cafe" },
  };
  const context = {
    building: { features: [basic, documented] },
    place: { features: [cafe, project] },
  };
  assert.deepEqual(propertyFeatures(context), [documented, basic, project]);
  assert.deepEqual(context.building.features, [basic, documented]);
  assert.deepEqual(propertyFeatures(null), []);
});

test("exports preserve original text and neutralize spreadsheet formulas", () => {
  const result = csv([["=1+1", 'name, "quoted"', "  +SUM(A1)", "normal"]]);
  assert.ok(result.includes("'=1+1"));
  assert.ok(result.includes("'  +SUM(A1)"));
  assert.ok(result.includes('"name, ""quoted"""'));
});

test("search handles accents and source names without translating evidence", () => {
  assert.equal(normalized("Île de Reem"), "ile de reem");
  assert.equal(normalized("الريم"), "الريم");
});

test("camera bounds preserve all polygon parts and holes", () => {
  assert.deepEqual(
    geometryBounds({
      type: "MultiPolygon",
      coordinates: [
        [
          [
            [54.4, 24.5],
            [54.42, 24.51],
            [54.4, 24.5],
          ],
          [
            [54.405, 24.503],
            [54.406, 24.504],
            [54.405, 24.503],
          ],
        ],
        [
          [
            [54.43, 24.49],
            [54.44, 24.495],
            [54.43, 24.49],
          ],
        ],
      ],
    }),
    [
      [54.4, 24.49],
      [54.44, 24.51],
    ],
  );
});
