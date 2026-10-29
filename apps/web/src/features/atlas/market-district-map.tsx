"use client";

import type { components } from "@property-platform/contracts";
import type { FeatureCollection } from "geojson";
import {
  type ErrorEvent,
  Map as LibreMap,
  LngLatBounds,
  NavigationControl,
  Popup,
  setWorkerUrl,
} from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { CitedRights } from "@/features/projects/cited-rights";
import { registerArchivedTiles } from "./archived-tiles";
import {
  HYDROGRAPHY_LAYERS,
  HYDROGRAPHY_SOURCE,
  PLAN_COLORS,
} from "./hydrography";
import { mapControlLabels } from "./map-style";
import styles from "./market-district-map.module.css";
import { geometryBounds } from "./presentation";
import type { MapLabels } from "./types";
import "maplibre-gl/dist/maplibre-gl.css";

type MarketData = components["schemas"]["DistrictMarketResponse"];
const countColors = ["#dfebe2", "#b1d0bd", "#75a98f", "#36785f", "#164c3b"];
const rateColors = ["#f2dfb5", "#d8b471", "#b6813b", "#855820", "#523510"];
setWorkerUrl(
  new URL(
    "maplibre-gl/dist/maplibre-gl-worker.mjs",
    import.meta.url,
  ).toString(),
);

export default function MarketDistrictMap({
  territory,
  snapshot,
  query,
  locale,
  m,
}: {
  territory: string;
  snapshot: string | null;
  query: string;
  locale: string;
  m: MapLabels;
}) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<MarketData | null>(null);
  const [failed, setFailed] = useState(false);
  const [metric, setMetric] = useState("sales");
  const element = useRef<HTMLElement>(null);
  const instance = useRef<LibreMap | null>(null);
  const popup = useRef<Popup | null>(null);
  useEffect(() => {
    if (!open) return;
    const abort = new AbortController();
    setFailed(false);
    setData(null);
    const params = new URLSearchParams({ territory, q: query });
    if (snapshot) params.set("snapshot_id", snapshot);
    void fetch(`/api/atlas/market-map?${params}`, { signal: abort.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("unavailable");
        const result = (await response.json()) as MarketData;
        if (!abort.signal.aborted) setData(result);
      })
      .catch(() => {
        if (!abort.signal.aborted) setFailed(true);
      });
    return () => abort.abort();
  }, [open, territory, snapshot, query]);
  useEffect(() => {
    if (!open || !element.current || !data) return;
    registerArchivedTiles();
    const extent = new LngLatBounds();
    for (const feature of data.features) {
      const bounds = geometryBounds(feature.geometry);
      if (bounds) extent.extend(bounds);
    }
    const map = new LibreMap({
      container: element.current,
      locale: mapControlLabels(m, m.marketMap),
      bounds: extent.isEmpty()
        ? [
            [54.15, 24.18],
            [54.85, 24.68],
          ]
        : extent,
      fitBoundsOptions: { padding: 25, animate: false },
      minZoom: 5,
      maxZoom: 17,
      style: {
        version: 8,
        sources: {
          hydrography: HYDROGRAPHY_SOURCE,
          market: {
            type: "geojson",
            data: data as unknown as FeatureCollection,
            attribution: "ADREC · DMT / Onwani",
          },
        },
        layers: [
          {
            id: "background",
            type: "background",
            paint: { "background-color": PLAN_COLORS.land },
          },
          ...HYDROGRAPHY_LAYERS,
          {
            id: "market-fill",
            type: "fill",
            source: "market",
            paint: { "fill-color": "#528779", "fill-opacity": 0.7 },
          },
          {
            id: "market-line",
            type: "line",
            source: "market",
            paint: { "line-color": "#245e56", "line-width": 1 },
          },
        ],
      },
    });
    instance.current = map;
    const onError = (event: ErrorEvent) => {
      if (!("sourceId" in event) || event.sourceId === "market")
        setFailed(true);
    };
    map.on("error", onError);
    map.addControl(new NavigationControl(), "top-right");
    const resize = new ResizeObserver(() => map.resize());
    resize.observe(element.current);
    const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
    map.on("click", (event) => {
      const feature = map.queryRenderedFeatures(event.point, {
        layers: ["market-fill"],
      })[0];
      if (!feature) return;
      const content = document.createElement("div"),
        title = document.createElement("strong"),
        values = document.createElement("p");
      title.textContent =
        locale === "ar"
          ? feature.properties.name_ar || feature.properties.name
          : feature.properties.name;
      values.textContent = `${number.format(Number(feature.properties.sales))} ${m.marketCount} · ${feature.properties.median_rate ? `${number.format(Number(feature.properties.median_rate))} AED/m²` : m.marketFew}`;
      content.append(title, values);
      popup.current?.remove();
      popup.current = new Popup()
        .setLngLat(event.lngLat)
        .setDOMContent(content)
        .addTo(map);
    });
    return () => {
      popup.current?.remove();
      resize.disconnect();
      instance.current = null;
      map.remove();
    };
  }, [open, data, locale, m]);
  useEffect(() => {
    const map = instance.current;
    if (!map || !data) return;
    const update = () =>
      map.setPaintProperty(
        "market-fill",
        "fill-color",
        metric === "sales"
          ? [
              "step",
              ["get", "sales"],
              countColors[0],
              10,
              countColors[1],
              50,
              countColors[2],
              200,
              countColors[3],
              1000,
              countColors[4],
            ]
          : [
              "case",
              ["==", ["get", "median_rate"], null],
              "#d3d5d0",
              [
                "step",
                ["to-number", ["get", "median_rate"]],
                rateColors[0],
                10000,
                rateColors[1],
                15000,
                rateColors[2],
                20000,
                rateColors[3],
                30000,
                rateColors[4],
              ],
            ],
      );
    if (map.isStyleLoaded()) update();
    else map.once("load", update);
    return () => {
      map.off("load", update);
    };
  }, [metric, data]);
  return (
    <details
      onToggle={(event) => setOpen(event.currentTarget.open)}
      className={styles.panel}
    >
      <summary>{m.marketMap}</summary>
      {open && (
        <>
          <label>
            {m.marketMap}
            <select
              value={metric}
              onChange={(event) => setMetric(event.target.value)}
            >
              <option value="sales">{m.marketCount}</option>
              <option value="rate">{m.marketRate}</option>
            </select>
          </label>
          <p className="small-text">{m.marketMapNote}</p>
          {!data || failed ? (
            <p role="status">
              {failed ? m.marketUnavailable : m.marketLoading}
            </p>
          ) : (
            <>
              <section
                ref={element}
                className={styles.canvas}
                aria-label={m.marketMap}
              />
              <div className={styles.legend}>
                {(metric === "sales"
                  ? ["0–9", "10–49", "50–199", "200–999", "≥1000"]
                  : [
                      "<10 000",
                      "10–15 000",
                      "15–20 000",
                      "20–30 000",
                      "≥30 000 AED/m²",
                      m.marketFew,
                    ]
                ).map((label, index) => (
                  <span key={label}>
                    <i
                      aria-hidden="true"
                      style={{
                        backgroundColor:
                          (metric === "sales" ? countColors : rateColors)[
                            index
                          ] ?? "#d3d5d0",
                      }}
                    />
                    {label}
                  </span>
                ))}
              </div>
              <p className="small-text">
                {new Intl.NumberFormat(locale).format(data.mapped_sales)}{" "}
                {m.marketCount} ·{" "}
                {new Intl.NumberFormat(locale).format(data.unmatched_sales)}{" "}
                {m.marketMissing}
              </p>
              <p className="small-text">
                <a
                  href={data.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  ADREC
                </a>{" "}
                ·{" "}
                <a
                  href={data.boundary_source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  DMT / Onwani
                </a>
              </p>
              <CitedRights rights={data.rights} />
              <CitedRights rights={data.boundary_rights} />
            </>
          )}
        </>
      )}
    </details>
  );
}
