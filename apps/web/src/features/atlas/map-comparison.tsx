"use client";

import { Map as LibreMap } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { BASEMAP_IMAGERY } from "./imagery-sources";
import styles from "./map-workbench.module.css";
import type { MapLabels } from "./types";

export function MapComparison({
  map,
  providerId,
  split,
  labels,
}: {
  map: LibreMap;
  providerId: string;
  split: number;
  labels: MapLabels;
}) {
  const root = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const provider = BASEMAP_IMAGERY.find((item) => item.id === providerId);
  useEffect(() => {
    if (!root.current || !provider) return;
    setFailed(false);
    const other = new LibreMap({
      container: root.current,
      interactive: false,
      attributionControl: false,
      center: map.getCenter(),
      zoom: map.getZoom(),
      pitch: map.getPitch(),
      bearing: map.getBearing(),
      minZoom: 0,
      maxZoom: 24,
      style: {
        version: 8,
        sources: {
          comparison: {
            type: "raster",
            tiles: [provider.tiles],
            tileSize: 256,
            minzoom: provider.minzoom,
            maxzoom: provider.maxzoom,
            attribution: provider.attribution,
          },
        },
        layers: [
          {
            id: "comparison",
            type: "raster",
            source: "comparison",
            paint: { "raster-fade-duration": 0 },
          },
        ],
      },
    });
    const sync = () =>
      other.jumpTo({
        center: map.getCenter(),
        zoom: map.getZoom(),
        pitch: map.getPitch(),
        bearing: map.getBearing(),
        padding: map.getPadding(),
      });
    const resize = new ResizeObserver(() => {
      other.resize();
      sync();
    });
    resize.observe(root.current);
    other.on("error", () => setFailed(true));
    map.on("move", sync);
    return () => {
      resize.disconnect();
      map.off("move", sync);
      other.remove();
    };
  }, [map, provider]);
  if (!provider) return null;
  return (
    <>
      <div
        className={styles.comparison}
        style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}
        ref={root}
        aria-hidden="true"
      />
      <div
        className={styles.divider}
        style={{ left: `${split}%` }}
        aria-hidden="true"
      />
      <p className={styles.compareCredit}>
        <a href={provider.sourceUrl} target="_blank" rel="noopener noreferrer">
          {provider.title}
        </a>{" "}
        · {provider.attribution}
        {failed && ` · ${labels.imageryUnavailable}`}
      </p>
    </>
  );
}
