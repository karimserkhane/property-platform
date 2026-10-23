"use client";

import type { components } from "@property-platform/contracts";
import type { FeatureCollection } from "geojson";
import type {
  GeoJSONSource,
  Map as LibreMap,
  MapMouseEvent,
} from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import { UiIcon } from "@/components/ui-icon";
import { BASEMAP_IMAGERY } from "./imagery-sources";
import {
  type AnalysisMode,
  type Coordinate,
  emptyAnalysis,
  measurement,
  projectsInZone,
  type SearchItem,
  searchItems,
  searchMap,
  setMapTool,
} from "./map-analysis";
import { MapComparison } from "./map-comparison";
import styles from "./map-workbench.module.css";
import { geometryBounds } from "./presentation";
import { updateProjectClusters } from "./project-clusters";
import { dubaiClock, shadowPolygons, solarInstant, sunlight } from "./solar";
import type { MapContext, MapLabels, ParcelRows } from "./types";

export function MapWorkbench({
  map,
  context,
  parcels,
  locale,
  m,
  territory,
  compact = false,
  places = true,
  names = true,
  onChoose,
}: {
  map: LibreMap | null;
  context: MapContext | null;
  parcels: ParcelRows | null;
  locale: string;
  m: MapLabels;
  territory: string;
  compact?: boolean;
  places?: boolean;
  names?: boolean;
  onChoose?: (item: SearchItem) => void;
}) {
  const root = useRef<HTMLDetailsElement>(null);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<AnalysisMode>("browse");
  const [points, setPoints] = useState<Coordinate[]>([]);
  const [finished, setFinished] = useState(false);
  const [drawKind, setDrawKind] = useState<"distance" | "zone">("distance");
  const [compare, setCompare] = useState(false);
  const [otherProvider, setOtherProvider] = useState(
    "sentinel-worldcover-2020",
  );
  const [split, setSplit] = useState(50);
  const [solar, setSolar] = useState(
    () =>
      typeof window !== "undefined" &&
      new URLSearchParams(window.location.search).get("sunlight") === "1",
  );
  const [clock, setClock] = useState(() => {
    const saved =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("sun")
        : null;
    return saved && solarInstant(saved) ? saved : dubaiClock();
  });
  const [shadows, setShadows] = useState(
    () =>
      typeof window !== "undefined" &&
      new URLSearchParams(window.location.search).get("shadows") === "1",
  );
  const [center, setCenter] = useState<Coordinate>([54.4, 24.5]);
  const [walking, setWalking] = useState<FeatureCollection | null>(null);
  const [walkState, setWalkState] = useState<"ready" | "loading" | "error">(
    "ready",
  );
  const [walkMinutes, setWalkMinutes] = useState(10);
  const [walkOrigin, setWalkOrigin] = useState<Coordinate | null>(null);
  const [walkEvidence, setWalkEvidence] = useState("");
  const inputs = useMemo(
    () => searchItems(context, parcels, locale),
    [context, parcels, locale],
  );
  const results = useMemo(() => searchMap(inputs, query), [inputs, query]);
  const measures = useMemo(
    () => measurement(points, finished && drawKind === "zone"),
    [points, finished, drawKind],
  );
  const inside = useMemo(
    () => projectsInZone(inputs, measures.polygon),
    [inputs, measures.polygon],
  );
  const sun = useMemo(
    () => sunlight(clock, center[0], center[1]),
    [clock, center],
  );
  const shadowData = useMemo(
    () =>
      solar && shadows
        ? shadowPolygons(
            context?.building.features ?? [],
            clock,
            center[0],
            center[1],
          )
        : emptyAnalysis(),
    [solar, shadows, context, clock, center],
  );
  const modeRef = useRef({ mode, finished });
  modeRef.current = { mode, finished };
  const drawingRef = useRef({ points, drawKind });
  drawingRef.current = { points, drawKind };
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  const formatTime = (date: Date | null | undefined) =>
    date
      ? new Intl.DateTimeFormat(locale, {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "Asia/Dubai",
        }).format(date)
      : "—";

  useEffect(() => {
    if (!map) return;
    const url = new URL(window.location.href);
    for (const key of ["sunlight", "sun", "shadows"])
      url.searchParams.delete(key);
    if (solar && solarInstant(clock)) {
      url.searchParams.set("sunlight", "1");
      url.searchParams.set("sun", clock);
      if (shadows) url.searchParams.set("shadows", "1");
    }
    window.history.replaceState(window.history.state, "", url);
  }, [map, solar, clock, shadows]);

  useEffect(() => {
    if (map) updateProjectClusters(map, context, places, names);
  }, [map, context, places, names]);
  useEffect(() => {
    if (!map) return;
    const sync = () => {
      const point = map.getCenter();
      setCenter([point.lng, point.lat]);
    };
    sync();
    map.on("moveend", sync);
    for (const id of [
      "analysis",
      "analysis-shadow",
      "analysis-walk",
      "analysis-origin",
    ])
      if (!map.getSource(id))
        map.addSource(id, { type: "geojson", data: emptyAnalysis() });
    map.addLayer({
      id: "analysis-zone",
      type: "fill",
      source: "analysis",
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: { "fill-color": "#eb7939", "fill-opacity": 0.15 },
    });
    map.addLayer({
      id: "analysis-line",
      type: "line",
      source: "analysis",
      filter: ["!=", ["geometry-type"], "Point"],
      paint: { "line-color": "#b74e19", "line-width": 3 },
    });
    map.addLayer({
      id: "analysis-points",
      type: "circle",
      source: "analysis",
      filter: ["==", ["geometry-type"], "Point"],
      paint: {
        "circle-color": "#ffffff",
        "circle-stroke-color": "#b74e19",
        "circle-stroke-width": 2,
        "circle-radius": 5,
      },
    });
    map.addLayer(
      {
        id: "analysis-shadow",
        type: "fill",
        source: "analysis-shadow",
        paint: { "fill-color": "#16253b", "fill-opacity": 0.25 },
      },
      map.getLayer("buildings") ? "buildings" : undefined,
    );
    map.addLayer({
      id: "analysis-walk",
      type: "fill",
      source: "analysis-walk",
      paint: { "fill-color": "#3c847a", "fill-opacity": 0.18 },
    });
    map.addLayer({
      id: "analysis-walk-line",
      type: "line",
      source: "analysis-walk",
      paint: { "line-color": "#24645b", "line-width": 2 },
    });
    map.addLayer({
      id: "analysis-origin",
      type: "circle",
      source: "analysis-origin",
      paint: {
        "circle-color": "#123e46",
        "circle-radius": 7,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 3,
      },
    });
    const click = (event: MapMouseEvent) => {
      const active = modeRef.current;
      if (active.mode === "browse") return;
      if (active.mode === "walk") {
        setWalkOrigin([event.lngLat.lng, event.lngLat.lat]);
        return;
      }
      if (active.finished) return;
      setPoints((previous) =>
        previous.length < 100
          ? [...previous, [event.lngLat.lng, event.lngLat.lat]]
          : previous,
      );
    };
    const key = (event: KeyboardEvent) => {
      if (modeRef.current.mode === "browse") return;
      if (event.key === "Escape") {
        setMode("browse");
        event.preventDefault();
      }
      if (
        event.key === "Enter" &&
        modeRef.current.mode !== "walk" &&
        drawingRef.current.points.length >=
          (drawingRef.current.drawKind === "zone" ? 3 : 2)
      ) {
        setFinished(true);
        setMode("browse");
        event.preventDefault();
      }
      if (event.key === "Backspace") {
        setPoints((value) => value.slice(0, -1));
        event.preventDefault();
      }
    };
    map.on("click", click);
    map.getCanvas().addEventListener("keydown", key);
    return () => {
      map.off("moveend", sync);
      map.off("click", click);
      map.getCanvas().removeEventListener("keydown", key);
      setMapTool(map, "browse");
      for (const id of [
        "analysis-zone",
        "analysis-line",
        "analysis-points",
        "analysis-shadow",
        "analysis-walk",
        "analysis-walk-line",
        "analysis-origin",
      ])
        if (map.getLayer(id)) map.removeLayer(id);
      for (const id of [
        "analysis",
        "analysis-shadow",
        "analysis-walk",
        "analysis-origin",
      ])
        if (map.getSource(id)) map.removeSource(id);
    };
  }, [map]);
  useEffect(() => {
    if (!map) return;
    setMapTool(map, mode);
    if (mode !== "browse") {
      map.doubleClickZoom.disable();
      map.getCanvas().style.cursor = "crosshair";
    } else {
      map.doubleClickZoom.enable();
      map.getCanvas().style.cursor = "";
    }
    return () => {
      map.doubleClickZoom.enable();
      map.getCanvas().style.cursor = "";
      setMapTool(map, "browse");
    };
  }, [map, mode]);
  useEffect(() => {
    if (!map?.getSource("analysis")) return;
    (map.getSource("analysis") as GeoJSONSource).setData(measures.data);
  }, [map, measures]);
  const baselineLight = useRef<ReturnType<LibreMap["getLight"]>>(undefined);
  useEffect(() => {
    baselineLight.current = map?.getLight();
    return () => {
      baselineLight.current = undefined;
    };
  }, [map]);
  useEffect(() => {
    if (!map) return;
    const light = solar && sun ? sun.light : baselineLight.current;
    if (light) map.setLight(light);
  }, [map, solar, sun]);
  useEffect(() => {
    if (!map?.getSource("analysis-shadow")) return;
    (map.getSource("analysis-shadow") as GeoJSONSource).setData(shadowData);
  }, [map, shadowData]);
  useEffect(() => {
    if (!walkOrigin) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const deadline = Date.now() + 180000;
    setWalkState("loading");
    setWalking(null);
    setWalkEvidence("");
    const read = async () => {
      try {
        const params = new URLSearchParams({
          territory,
          longitude: walkOrigin[0].toFixed(5),
          latitude: walkOrigin[1].toFixed(5),
          minutes: String(walkMinutes),
        });
        const response = await fetch(`/api/atlas/accessibility?${params}`, {
          signal: controller.signal,
        });
        if (response.status === 202 && Date.now() < deadline) {
          timer = setTimeout(read, 3000);
          return;
        }
        if (response.status !== 200) throw new Error("unavailable");
        const result =
          (await response.json()) as components["schemas"]["WalkingResponse"];
        if (controller.signal.aborted) return;
        setWalking(result.collection as FeatureCollection);
        setWalkEvidence(result.ingested_at);
        setWalkState("ready");
        const bounds = geometryBounds(result.collection.features[0]?.geometry);
        if (map && bounds)
          map.fitBounds(bounds, {
            padding: compact ? 45 : 80,
            maxZoom: 16,
            duration: window.matchMedia("(prefers-reduced-motion: reduce)")
              .matches
              ? 0
              : 250,
          });
      } catch {
        if (!controller.signal.aborted) setWalkState("error");
      }
    };
    void read();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [territory, walkOrigin, walkMinutes, map, compact]);
  useEffect(() => {
    if (map?.getSource("analysis-origin"))
      (map.getSource("analysis-origin") as GeoJSONSource).setData({
        type: "FeatureCollection",
        features: walkOrigin
          ? [
              {
                type: "Feature",
                properties: {},
                geometry: { type: "Point", coordinates: walkOrigin },
              },
            ]
          : [],
      });
  }, [map, walkOrigin]);
  useEffect(() => {
    if (map?.getSource("analysis-walk"))
      (map.getSource("analysis-walk") as GeoJSONSource).setData(
        walking ?? emptyAnalysis(),
      );
  }, [map, walking]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape" && root.current?.open) {
        root.current.open = false;
        setMode("browse");
        root.current.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, []);

  const choose = (item: SearchItem) => {
    if (!map) return;
    const bounds = geometryBounds(item.geometry);
    if (bounds)
      map.fitBounds(bounds, {
        maxZoom: 16.5,
        padding: compact ? 50 : 90,
        duration: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? 0
          : 250,
      });
    onChoose?.(item);
    setQuery("");
    if (root.current) root.current.open = false;
  };
  const begin = (next: AnalysisMode) => {
    setMode(next);
    if (next === "zone" || next === "distance") {
      setDrawKind(next);
      setPoints([]);
      setFinished(false);
    }
  };
  if (!map) return null;
  return (
    <>
      {compare && (
        <MapComparison
          map={map}
          providerId={otherProvider}
          split={split}
          labels={m}
        />
      )}
      {solar && sun && (
        <div
          className={styles.solarTint}
          style={{ opacity: sun.daylight ? 0.18 * (1 - sun.elevation) : 0.62 }}
          aria-hidden="true"
        />
      )}
      <details
        ref={root}
        className={`${styles.dock} ${compact ? styles.compact : ""}`}
        name="explore-map-controls"
        onToggle={(event) => {
          if (!event.currentTarget.open) setMode("browse");
        }}
      >
        <summary>
          <UiIcon name="search" />
          {m.analysisTools}
        </summary>
        <div className={styles.panel}>
          <label>
            {m.searchMap}
            <input
              type="search"
              maxLength={80}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={m.searchMap}
            />
          </label>
          <p className={styles.note}>{m.analysisScope}</p>
          {query.trim().length >= 2 && (
            <div className={styles.results}>
              {results.length ? (
                results.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => choose(item)}
                  >
                    <bdi>{item.name}</bdi>
                  </button>
                ))
              ) : (
                <p role="status">{m.searchEmpty}</p>
              )}
            </div>
          )}
          <div className={styles.row}>
            <button
              type="button"
              aria-pressed={mode === "distance"}
              onClick={() => begin("distance")}
            >
              {m.measureDistance}
            </button>
            <button
              type="button"
              aria-pressed={mode === "zone"}
              onClick={() => begin("zone")}
            >
              {m.drawZone}
            </button>
            <button
              type="button"
              aria-pressed={mode === "walk"}
              onClick={() => begin("walk")}
            >
              {m.walkArea}
            </button>
          </div>
          {(mode === "distance" || mode === "zone") && (
            <p className={styles.note}>{m.drawHint}</p>
          )}
          {points.length > 0 && (
            <>
              <output className={styles.reading}>
                {number.format(measures.metres)} m
                {measures.polygon && (
                  <>
                    {" "}
                    · {number.format(measures.squareMetres)} m² ·{" "}
                    {inside.length} {m.zoneProjects}
                  </>
                )}
              </output>
              <div className={styles.row}>
                <button
                  type="button"
                  disabled={
                    finished || points.length < (drawKind === "zone" ? 3 : 2)
                  }
                  onClick={() => {
                    setFinished(true);
                    setMode("browse");
                  }}
                >
                  {m.finishDrawing}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setPoints((value) => value.slice(0, -1));
                    setFinished(false);
                    setMode(drawKind);
                  }}
                >
                  {m.undoDrawing}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setPoints([]);
                    setFinished(false);
                    setMode("browse");
                  }}
                >
                  {m.clearDrawing}
                </button>
              </div>
              {inside.length > 0 && (
                <div className={styles.results}>
                  {inside.slice(0, 12).map((item) => (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() => choose(item)}
                    >
                      <bdi>{item.name}</bdi>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
          {(mode === "walk" || walkOrigin) && (
            <>
              <label>
                {m.walkArea}
                <select
                  value={walkMinutes}
                  onChange={(event) =>
                    setWalkMinutes(Number(event.target.value))
                  }
                >
                  {[5, 10, 15].map((minutes) => (
                    <option key={minutes} value={minutes}>
                      {minutes} min
                    </option>
                  ))}
                </select>
              </label>
              <p className={styles.note}>{m.walkOrigin}</p>
              {walkState !== "ready" && (
                <p role="status">
                  {
                    m[
                      walkState === "loading"
                        ? "walkPending"
                        : "walkUnavailable"
                    ]
                  }
                </p>
              )}
              {walkOrigin && (
                <button
                  type="button"
                  onClick={() => {
                    setWalking(null);
                    setWalkOrigin(null);
                    setMode("browse");
                  }}
                >
                  {m.clearDrawing}
                </button>
              )}
              <p className={styles.note}>
                {m.walkNote}
                {walkEvidence && (
                  <>
                    {" "}
                    ·{" "}
                    {new Intl.DateTimeFormat(locale, {
                      dateStyle: "short",
                      timeStyle: "short",
                      timeZone: "Asia/Dubai",
                    }).format(new Date(walkEvidence))}
                  </>
                )}
              </p>
            </>
          )}
          <hr />
          <label className={styles.check}>
            <input
              type="checkbox"
              checked={compare}
              onChange={(event) => setCompare(event.target.checked)}
            />
            {m.compareMaps}
          </label>
          {compare && (
            <>
              <label>
                {m.compareWith}
                <select
                  value={otherProvider}
                  onChange={(event) => setOtherProvider(event.target.value)}
                >
                  {BASEMAP_IMAGERY.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {m.compareSwipe}
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={split}
                  onChange={(event) => setSplit(Number(event.target.value))}
                />
              </label>
              <p className={styles.note}>{m.compareNote}</p>
            </>
          )}
          <hr />
          <label className={styles.check}>
            <input
              type="checkbox"
              checked={solar}
              onChange={(event) => setSolar(event.target.checked)}
            />
            {m.solarSimulation}
          </label>
          {solar && (
            <>
              <label>
                {m.solarDate}
                <input
                  type="date"
                  min="2000-01-01"
                  max="2099-12-31"
                  value={clock.slice(0, 10)}
                  onInput={(event) =>
                    setClock(`${event.currentTarget.value}T${clock.slice(11)}`)
                  }
                />
              </label>
              <label>
                {m.solarTime} · Asia/Dubai (UTC+4)
                <input
                  type="time"
                  value={clock.slice(11)}
                  onInput={(event) =>
                    setClock(
                      `${clock.slice(0, 10)}T${event.currentTarget.value}`,
                    )
                  }
                />
              </label>
              <label>
                {m.solarTime}
                <input
                  type="range"
                  min="0"
                  max="1435"
                  step="5"
                  value={
                    Number(clock.slice(11, 13)) * 60 +
                      Number(clock.slice(14, 16)) || 0
                  }
                  onChange={(event) => {
                    const minute = Number(event.target.value);
                    setClock(
                      `${clock.slice(0, 10)}T${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`,
                    );
                  }}
                />
              </label>
              {sun && (
                <div className={styles.reading} aria-live="polite">
                  {m[sun.daylight ? "solarDay" : "solarNight"]}
                  <br />
                  {m.solarAzimuth}: {number.format(sun.azimuth)}° ·{" "}
                  {m.solarAltitude}: {number.format(sun.altitude)}°<br />
                  {m.solarRise}: {formatTime(sun.sunrise)} · {m.solarSet}:{" "}
                  {formatTime(sun.sunset)}
                </div>
              )}
              <label className={styles.check}>
                <input
                  type="checkbox"
                  checked={shadows}
                  onChange={(event) => setShadows(event.target.checked)}
                />
                {m.solarShadows}
              </label>
              {shadows && (
                <p className={styles.note}>
                  {number.format(shadowData.features.length)} · {m.solarShadows}
                  <br />
                  {m.solarShadowNote}
                </p>
              )}
              <p className={styles.note}>{m.solarNote}</p>
            </>
          )}
        </div>
      </details>
    </>
  );
}
