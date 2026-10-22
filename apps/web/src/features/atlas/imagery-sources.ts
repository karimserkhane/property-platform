export const IMAGERY_ATTRIBUTION =
  "Esri, Maxar, Earthstar Geographics and the GIS User Community";

type ImageryProvider = {
  id: string;
  layerId: string;
  title: string;
  tiles: string;
  minzoom: number;
  maxzoom: number;
  attribution: string;
  sourceUrl: string;
  year: number | null;
};

/** Global basemaps only. A bounded observation is never offered as a basemap. */
export const BASEMAP_IMAGERY: readonly ImageryProvider[] = [
  {
    id: "esri",
    layerId: "satellite",
    title: "Esri World Imagery",
    tiles:
      "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    // Tilemap qualification on Reem: imagery exists at z19, but z20/z21
    // return HTTP 200 grey "Map data not yet available" placeholders.
    // Keep source tiles at z19; MapLibre can still zoom in by enlarging them.
    maxzoom: 19,
    minzoom: 0,
    attribution: IMAGERY_ATTRIBUTION,
    sourceUrl:
      "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer",
    year: null,
  },
  ...[2021, 2020].map((year) => ({
    id: `sentinel-worldcover-${year}`,
    layerId: `satellite-worldcover-${year}`,
    title: `Sentinel-2 · ESA WorldCover · ${year} · 10 m`,
    tiles: `archive://sentinel-worldcover-${year}/{z}/{x}/{y}`,
    minzoom: 8,
    maxzoom: 14,
    attribution: `© ESA WorldCover project ${year} / Contains modified Copernicus Sentinel data (${year}) processed by ESA WorldCover consortium · Terrascope · CC BY 4.0`,
    sourceUrl: "https://esa-worldcover.org/en/data-access",
    year,
  })),
];

/** Exactly one source, never an Esri fallback under Sentinel or missing data. */
export function imageryVisibility(
  satellite: boolean,
  scene: string,
): Record<string, boolean> {
  return Object.fromEntries(
    BASEMAP_IMAGERY.map((item) => [
      item.layerId,
      satellite && item.id === scene,
    ]),
  );
}

/** Preserve the chosen source across territories, locale changes and reloads. */
export function imagerySelection(value: string | null) {
  const provider = BASEMAP_IMAGERY.find((item) => item.id === value);
  return { satellite: Boolean(provider), scene: provider?.id ?? "esri" };
}
