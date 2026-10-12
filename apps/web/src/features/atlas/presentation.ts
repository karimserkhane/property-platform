import type { MapFeature, MapLabels } from "./types";

type MapHit = {
  layer: { id: string };
  properties?: Record<string, unknown> | null;
};

// Rendering order is visual, not the specificity of the object under the pointer.
// A ProjectLimits parcel (for example RT4_TMP_PL2) must not hide a real plot.
export function selectMapHit<T extends MapHit>(hits: readonly T[]): T | null {
  let selected: T | null = null;
  let priority = Infinity;
  for (const hit of hits) {
    if (!hit.properties?.id) continue;
    const rank =
      hit.layer.id === "buildings"
        ? 0
        : hit.layer.id === "parcel-fill"
          ? hit.properties.category === "overlay"
            ? 4
            : 1
          : hit.layer.id === "places"
            ? 2
            : hit.layer.id === "streets"
              ? 3
              : hit.layer.id === "area-hit"
                ? hit.properties.kind === "district"
                  ? 6
                  : 5
                : Infinity;
    if (rank < priority) {
      selected = hit;
      priority = rank;
    }
  }
  return selected;
}

export function geometryBounds(
  geometry: MapFeature["geometry"],
): [[number, number], [number, number]] | null {
  const numbers = geometry.coordinates.flat(Infinity) as number[];
  if (numbers.length < 2) return null;
  let west = Infinity,
    south = Infinity,
    east = -Infinity,
    north = -Infinity;
  for (let i = 0; i < numbers.length; i += 2) {
    west = Math.min(west, numbers[i]);
    east = Math.max(east, numbers[i]);
    south = Math.min(south, numbers[i + 1]);
    north = Math.max(north, numbers[i + 1]);
  }
  return [
    [west, south],
    [east, north],
  ];
}

export function sourceLabel(reliability: string, labels: MapLabels) {
  return reliability === "official"
    ? labels.official
    : reliability === "publisher"
      ? labels.developer
      : reliability === "broker"
        ? labels.broker
        : labels.community;
}

export const COLORS = {
  mixed: "#d9bf95",
  residential: "#eedfae",
  green: "#bfdbb6",
  public: "#a9ccdf",
  tech: "#c7cdd3",
  rail: "#ac83bc",
  overlay: "#b9a5c3",
  unknown: "#e7e3d7",
} as const;
export type Category = keyof typeof COLORS;
export function normalized(value: string) {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}
export function csv(rows: (string | number | null | undefined)[][]) {
  return rows
    .map((row) =>
      row
        .map((value) => {
          let text = String(value ?? "");
          if (/^[\s]*[=+@-]/u.test(text)) text = `'${text}`;
          return `"${text.replaceAll('"', '""')}"`;
        })
        .join(","),
    )
    .join("\r\n");
}
export function download(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
