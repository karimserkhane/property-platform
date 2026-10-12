import type { MapFeature, MapLabels } from "./types";

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
