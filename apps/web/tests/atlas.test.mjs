import assert from "node:assert/strict";
import test from "node:test";
import {
  csv,
  districtBounds,
  geometryBounds,
  geometryClickArea,
  listedRights,
  normalized,
  parcelMapLabels,
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

test("whole area frames both island districts, excluding unrelated community bounds", () => {
  const area = (kind, coordinates) => ({
    properties: { kind },
    geometry: { type: "MultiPolygon", coordinates: [[coordinates]] },
  });
  const reem = area("district", [
    [54.39, 24.47],
    [54.43, 24.52],
  ]);
  const saadiyat = area("district", [
    [54.385, 24.49],
    [54.48, 24.6],
  ]);
  const community = area("community", [
    [51, 22],
    [57, 27],
  ]);
  const expected = [
    [54.385, 24.47],
    [54.48, 24.6],
  ];
  assert.deepEqual(districtBounds([reem, community, saadiyat]), expected);
  assert.deepEqual(districtBounds([saadiyat, reem]), expected);
  assert.deepEqual(districtBounds([reem]), [
    [54.39, 24.47],
    [54.43, 24.52],
  ]);
  assert.equal(districtBounds([community]), null);
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
  assert.equal(selectMapHit([overlay, sector]), overlay);
  assert.equal(selectMapHit([overlay]), overlay);
});

test("districts and sectors are the last selectable fallback", () => {
  const district = hit("area-hit", "island", { kind: "district" });
  const sector = hit("area-hit", "RT4", { kind: "community" });
  const overlay = hit("parcel-fill", "RT4_TMP_PL2", { category: "overlay" });
  const place = hit("places", "place");
  const street = hit("streets", "street");
  assert.equal(selectMapHit([district, sector]), district);
  assert.equal(selectMapHit([district]), district);
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
  assert.equal(selectMapHit([project, building, parcel]), project);
  assert.equal(selectMapHit([building, parcel, project]), project);
});

test("property labels and other named places win over RT7 TMP2, with land as fallback", () => {
  const land = hit("parcel-fill", "RT7_TMP2", { category: "mixed" });
  const label = hit("place-names", "project", {
    kind: "publisher_project_marker",
  });
  const place = hit("places", "tower", { kind: "apartments" });
  const street = hit("street-names", "street");
  assert.equal(selectMapHit([land, label]), label);
  assert.equal(selectMapHit([land, place]), place);
  assert.equal(selectMapHit([land, street]), street);
  assert.equal(selectMapHit([land]), land);
});

test("large RT7 TMP2 cannot hide a smaller overlapping parcel, regardless of paint order", () => {
  const broad = hit("parcel-fill", "RT7_TMP2", { category: "mixed" });
  const unit = hit("parcel-fill", "RT7_C1", { category: "mixed" });
  const area = new Map([
    ["RT7_TMP2", 1000],
    ["RT7_C1", 10],
  ]);
  assert.equal(selectMapHit([broad, unit], area), unit);
  assert.equal(selectMapHit([unit, broad], area), unit);
  assert.equal(selectMapHit([broad], area), broad);
  const shape = {
    type: "MultiPolygon",
    coordinates: [
      [
        [
          [54, 24],
          [58, 24],
          [58, 28],
          [54, 28],
          [54, 24],
        ],
        [
          [55, 25],
          [56, 25],
          [56, 26],
          [55, 26],
          [55, 25],
        ],
      ],
    ],
  };
  assert.equal(geometryClickArea(shape), 15);
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

test("parcel labels retain source uses and mark spatial project names as candidates", () => {
  const parcel = (id, land_use, category, use_types = []) => ({
    id,
    type: "Feature",
    geometry: { type: "MultiPolygon", coordinates: [] },
    properties: { id, code: id, land_use, category, use_types },
  });
  const data = {
    type: "FeatureCollection",
    features: [
      parcel("school", "Schools", "public", ["school"]),
      parcel("temporary", "Data Center", "tech"),
      parcel("project", "Commercial", "mixed"),
      parcel("sector", "ProjectLimits", "overlay"),
    ],
  };
  const projects = new Map([
    [
      "project",
      [candidate("marker", "The District", "publisher_project_marker")],
    ],
  ]);
  const result = parcelMapLabels(data, projects, "fr", (type) =>
    type === "school" ? "École" : type,
  );
  assert.deepEqual(
    result.features.map((f) => f.properties.display_name),
    ["École", "Data Center", "≈ The District", ""],
  );
  assert.equal(result.features[2].properties.potential_name, true);
  assert.equal(result.features[0].properties.potential_name, false);
  assert.equal(data.features[0].properties.land_use, "Schools");
  assert.equal(data.features[2].properties.display_name, undefined);
});

test("clickable parcel name labels retain building, place and street priority", () => {
  const label = hit("parcel-project-names", "parcel");
  const building = hit("buildings", "building");
  assert.equal(selectMapHit([label, building]), building);
  assert.equal(selectMapHit([label]), label);
  const project = hit("project-names", "project", {
    kind: "publisher_project_marker",
  });
  assert.equal(selectMapHit([label, project]), project);
  const use = hit("parcel-use-names", "use");
  const street = hit("street-names", "street");
  assert.equal(selectMapHit([use, street]), street);
});

test("a map feature finds the rights of its site in its lists", () => {
  const osm = { licence: "ODbL-1.0", publication: "open" };
  const psi = {
    licence: "proprietary",
    publication: "none",
    shown_beyond_terms: true,
  };
  const lists = [
    { sources: [{ url: "https://osm.example/", name: "OSM", rights: osm }] },
    null,
    { sources: [{ url: "https://psi.example/", name: "PSI", rights: psi }] },
  ];
  assert.equal(listedRights("https://psi.example/", lists), psi);
  assert.equal(listedRights("https://osm.example/", lists), osm);
  // An uncited page or a missing URL states no rights rather than guessing.
  assert.equal(listedRights("https://other.example/", lists), null);
  assert.equal(listedRights(undefined, lists), null);
});
