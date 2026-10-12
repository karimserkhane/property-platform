"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "@/i18n/navigation";
import { Inspector } from "./inspector";
import type { MapOptions, MapView } from "./parcel-map";
import {
  type Category,
  COLORS,
  csv,
  download,
  normalized,
  sourceLabel,
} from "./presentation";
import { References } from "./references";
import type {
  AtlasLabels,
  ImageryScene,
  MapContext,
  MapFeature,
  MapLabels,
  ParcelCollection,
  ParcelDetail,
  ResearchReference,
} from "./types";

const ParcelMap = dynamic(() => import("./parcel-map"), { ssr: false });
const REEM = "54.385,24.465,54.445,24.530";
type Tab =
  | "parcels"
  | "places"
  | "streets"
  | "buildings"
  | "future"
  | "sources";
const TABS: Tab[] = [
  "parcels",
  "places",
  "streets",
  "buildings",
  "future",
  "sources",
];

export function Explorer({
  labels,
  mapLabels: m,
  locale,
}: {
  labels: AtlasLabels;
  mapLabels: MapLabels;
  locale: string;
}) {
  const [collection, setCollection] = useState<ParcelCollection | null>(null);
  const [context, setContext] = useState<MapContext | null>(null);
  const [contextError, setContextError] = useState(false);
  const [references, setReferences] = useState<ResearchReference[]>([]);
  const [imagery, setImagery] = useState<ImageryScene[]>([]);
  const [referenceError, setReferenceError] = useState(false);
  const [detail, setDetail] = useState<ParcelDetail | null>(null);
  const [feature, setFeature] = useState<MapFeature | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("");
  const [use, setUse] = useState("");
  const [temps, setTemps] = useState(true);
  const [tab, setTab] = useState<Tab>("parcels");
  const [page, setPage] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [detailState, setDetailState] = useState<"loading" | "ready" | "error">(
    "ready",
  );
  const [mapFailed, setMapFailed] = useState(false);
  const [options, setOptions] = useState<MapOptions>({
    streets: true,
    buildings: true,
    places: true,
    areas: true,
    names: true,
    codes: false,
    satellite: false,
    scene: "esri",
  });
  const [view, setView] = useState<MapView>({ kind: "island", token: 0 });
  const requestId = useRef(0);
  const detailRequest = useRef<AbortController | null>(null);
  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt retries the same bounded read.
  useEffect(() => {
    const controller = new AbortController();
    setState("loading");
    setContextError(false);
    setReferenceError(false);
    fetch("/api/atlas/references", { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error("unavailable");
        setReferences(await r.json());
      })
      .catch(() => {
        if (!controller.signal.aborted) setReferenceError(true);
      });
    fetch(`/api/atlas/parcels?bbox=${REEM}`, { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error("unavailable");
        const data = (await r.json()) as ParcelCollection;
        if (!Array.isArray(data.features)) throw new Error("invalid");
        setCollection(data);
        setState("ready");
      })
      .catch(() => {
        if (!controller.signal.aborted) setState("error");
      });
    fetch(`/api/atlas/map-context?bbox=${REEM}`, { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error("unavailable");
        setContext((await r.json()) as MapContext);
      })
      .catch(() => {
        if (!controller.signal.aborted) setContextError(true);
      });
    return () => controller.abort();
  }, [attempt]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt retries a failed bounded read; immutable previews stay loaded.
  useEffect(() => {
    if (!options.satellite || imagery.length) return;
    const controller = new AbortController();
    fetch("/api/atlas/imagery", { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error("unavailable");
        setImagery(await r.json());
      })
      .catch(() => {
        if (!controller.signal.aborted) setContextError(true);
      });
    return () => controller.abort();
  }, [options.satellite, imagery.length, attempt]);

  async function select(id: string) {
    detailRequest.current?.abort();
    detailRequest.current = new AbortController();
    const current = ++requestId.current;
    setSelected(id);
    const parcelFeature = collection?.features.find((f) => f.id === id);
    if (parcelFeature)
      setView((v) => ({
        kind: "feature",
        token: v.token + 1,
        feature: parcelFeature,
      }));
    setFeature(null);
    setDetail(null);
    setDetailState("loading");
    const url = new URL(window.location.href);
    url.searchParams.set("parcel", id);
    window.history.replaceState(null, "", url);
    try {
      const r = await fetch(`/api/atlas/parcels/${id}`, {
        signal: AbortSignal.any([
          detailRequest.current.signal,
          AbortSignal.timeout(8000),
        ]),
      });
      if (!r.ok) throw new Error("unavailable");
      const data = (await r.json()) as ParcelDetail;
      if (current === requestId.current) {
        setDetail(data);
        setDetailState("ready");
      }
    } catch {
      if (current === requestId.current) setDetailState("error");
    }
  }
  function choose(f: MapFeature) {
    detailRequest.current?.abort();
    ++requestId.current;
    setFeature(f);
    setDetail(null);
    setSelected(null);
    setDetailState("ready");
    const url = new URL(window.location.href);
    url.searchParams.delete("parcel");
    window.history.replaceState(null, "", url);
    setView((v) => ({ kind: "feature", token: v.token + 1, feature: f }));
  }
  const initialSelection = useRef(false);
  useEffect(() => {
    if (initialSelection.current) return;
    initialSelection.current = true;
    const id = new URL(window.location.href).searchParams.get("parcel");
    if (id && /^[0-9a-f-]{36}$/i.test(id)) void select(id);
  });

  const placesByParcel = useMemo(() => {
    const names = new Map<string, string[]>();
    for (const f of context?.place.features ?? [])
      for (const id of f.properties.parcel_ids)
        names.set(id, [
          ...(names.get(id) ?? []),
          f.properties.name,
          f.properties.name_ar,
        ]);
    return names;
  }, [context]);
  const parcelCodes = useMemo(
    () =>
      Object.fromEntries(
        collection?.features.map((f) => [f.id, f.properties.code]) ?? [],
      ),
    [collection],
  );
  const filtered = useMemo(
    () =>
      collection
        ? {
            ...collection,
            features: collection.features.filter((f) => {
              const p = f.properties;
              return (
                (!sector || p.community === sector) &&
                (!use || p.category === use) &&
                (temps || !/(?:TMP|temporary)/i.test(p.code)) &&
                (!query ||
                  normalized(
                    [
                      p.code,
                      p.community,
                      p.land_use,
                      ...(placesByParcel.get(p.id) ?? []),
                    ].join(" "),
                  ).includes(normalized(query)))
              );
            }),
          }
        : null,
    [collection, sector, use, temps, query, placesByParcel],
  );
  const target =
    tab === "streets" ? "street" : tab === "buildings" ? "building" : "place";
  const mapItems = (context?.[target].features ?? []).filter(
    (f) =>
      !query ||
      normalized(
        [f.properties.name, f.properties.name_ar, f.properties.kind].join(" "),
      ).includes(normalized(query)),
  );
  const parcelItems =
    tab === "future"
      ? (filtered?.features.filter(
          (f) =>
            f.properties.category === "rail" ||
            /not constructed/i.test(f.properties.construction_status),
        ) ?? [])
      : (filtered?.features ?? []);
  const referenceItems = references.filter(
    (r) =>
      !query ||
      normalized([r.title, r.label, r.source_kind].join(" ")).includes(
        normalized(query),
      ),
  );
  const count =
    tab === "future" || tab === "sources"
      ? referenceItems.length
      : tab === "parcels"
        ? parcelItems.length
        : mapItems.length;
  const maxPage = Math.max(0, Math.ceil(count / 40) - 1);
  const currentPage = Math.min(page, maxPage);
  const sectors = [
    ...new Set(collection?.features.map((f) => f.properties.community) ?? []),
  ].sort();
  function changeTab(t: Tab) {
    setTab(t);
    setPage(0);
  }
  function frame(kind: MapView["kind"]) {
    setView((v) => ({ kind, token: v.token + 1 }));
  }
  function exportCSV() {
    const rows = [
      [m.parcels, m.areas, m.landUse, m.construction, labels.source],
      ...(filtered?.features ?? []).map((f) => [
        f.properties.code,
        f.properties.community,
        f.properties.land_use,
        f.properties.construction_status,
        "https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/0",
      ]),
    ];
    download(
      new Blob(["\uFEFF", csv(rows)], { type: "text/csv;charset=utf-8" }),
      "al-reem-parcels.csv",
    );
  }
  return (
    <main className="explore-shell atlas-shell">
      <div className="explore-heading">
        <div>
          <p className="eyebrow">{labels.pilot}</p>
          <h1>{labels.explore}</h1>
        </div>
        <Link className="text-link" href="/">
          {labels.back}
        </Link>
      </div>
      <div className="atlas-workspace">
        <section className="map-column" aria-label={labels.map}>
          <fieldset className="atlas-toolbar" aria-label={m.layers}>
            {(["island", "rt4", "near"] as const).map((kind) => (
              <button key={kind} type="button" onClick={() => frame(kind)}>
                {
                  m[
                    kind === "island"
                      ? "viewIsland"
                      : kind === "rt4"
                        ? "viewRT4"
                        : "viewNear"
                  ]
                }
              </button>
            ))}
            {(
              [
                "streets",
                "buildings",
                "places",
                "areas",
                "names",
                "codes",
              ] as const
            ).map((key) => (
              <button
                key={key}
                type="button"
                aria-pressed={options[key]}
                onClick={() => setOptions((o) => ({ ...o, [key]: !o[key] }))}
              >
                {m[key]}
              </button>
            ))}
            <button
              type="button"
              aria-pressed={options.satellite}
              onClick={() =>
                setOptions((o) => ({ ...o, satellite: !o.satellite }))
              }
            >
              {options.satellite ? m.plan : m.satellite}
            </button>
            <button type="button" onClick={exportCSV}>
              {m.exportCSV}
            </button>
            <button
              type="button"
              disabled={
                state !== "ready" || !context || contextError || mapFailed
              }
              onClick={() => frame("export")}
            >
              {m.exportPNG}
            </button>
          </fieldset>
          {options.satellite && (
            <div className="atlas-imagery-picker">
              <label>
                <span>{m.satellite}</span>{" "}
                <select
                  value={options.scene}
                  onChange={(e) =>
                    setOptions((o) => ({ ...o, scene: e.target.value }))
                  }
                >
                  <option value="esri">Esri World Imagery</option>
                  {imagery.map((scene) => (
                    <option key={scene.id} value={scene.id}>
                      Sentinel-2 · {scene.acquired_at.slice(0, 10)} ·{" "}
                      {scene.resolution_m} m
                    </option>
                  ))}
                </select>
              </label>
              {imagery
                .filter((scene) => scene.id === options.scene)
                .map((scene) => (
                  <p key={scene.id}>
                    <a
                      href={scene.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {labels.source} ↗
                    </a>
                    {" · "}
                    {m.sourceDate}:{" "}
                    {new Intl.DateTimeFormat(locale, {
                      dateStyle: "medium",
                      timeStyle: "short",
                      timeZone: "Asia/Dubai",
                    }).format(new Date(scene.acquired_at))}
                  </p>
                ))}
            </div>
          )}
          <div className="map-frame">
            {filtered && !mapFailed && (
              <ParcelMap
                data={filtered}
                context={context}
                selected={selected}
                onSelect={select}
                onFeature={choose}
                onError={() => setMapFailed(true)}
                label={labels.map}
                options={options}
                view={view}
                locale={locale}
                imagery={imagery}
                m={m}
              />
            )}
            {(state !== "ready" || mapFailed) && (
              <div className="map-status" role="status">
                <p>
                  {state === "loading" ? labels.loading : labels.unavailable}
                </p>
                <button
                  type="button"
                  className="button"
                  onClick={() => {
                    setMapFailed(false);
                    setAttempt((v) => v + 1);
                  }}
                >
                  {labels.retry}
                </button>
              </div>
            )}
            <details className="map-legend" open>
              <summary>{m.legend}</summary>
              <p className="small-text">
                <i style={{ backgroundColor: "#eb7939" }} />{" "}
                {m.projectReference} · {m.unverified}
              </p>
              {Object.entries(COLORS).map(([key, color]) => (
                <button
                  key={key}
                  type="button"
                  aria-pressed={use === key}
                  onClick={() => {
                    setUse((u) => (u === key ? "" : key));
                    setPage(0);
                  }}
                >
                  <i style={{ backgroundColor: color }} />
                  <span>{m[key as Category]}</span>
                </button>
              ))}
            </details>
          </div>
          <p className="map-credit">
            DMT / Onwani ·{" "}
            <a
              href="https://www.openstreetmap.org/copyright"
              target="_blank"
              rel="noopener noreferrer"
            >
              © OpenStreetMap contributors · ODbL
            </a>
          </p>
          {options.satellite && <p className="small-text">{m.imageryNote}</p>}
          {contextError && (
            <p role="status">
              {labels.unavailable}{" "}
              <button type="button" onClick={() => setAttempt((v) => v + 1)}>
                {labels.retry}
              </button>
            </p>
          )}
          {(collection?.truncated ||
            Object.values(context ?? {}).some((layer) => layer.truncated)) && (
            <p role="status">{labels.truncated}</p>
          )}
        </section>
        <aside className="atlas-sidebar" aria-label={labels.select}>
          <div className="atlas-tabs" role="tablist" aria-label={m.layers}>
            {TABS.map((t) => (
              <button
                type="button"
                role="tab"
                aria-selected={tab === t}
                aria-controls="atlas-panel"
                id={`tab-${t}`}
                key={t}
                onClick={() => changeTab(t)}
              >
                {t === "sources" ? labels.sources : m[t]}
              </button>
            ))}
          </div>
          <div
            id="atlas-panel"
            role="tabpanel"
            aria-labelledby={`tab-${tab}`}
            className="atlas-panel"
          >
            <label className="atlas-search">
              <span>{m.searchPrompt}</span>
              <input
                type="search"
                value={query}
                maxLength={80}
                dir="auto"
                onChange={(e) => {
                  setQuery(e.target.value);
                  setPage(0);
                }}
              />
            </label>
            <div className="atlas-filters">
              <select
                aria-label={m.allSectors}
                value={sector}
                onChange={(e) => {
                  setSector(e.target.value);
                  setPage(0);
                }}
              >
                <option value="">{m.allSectors}</option>
                {sectors.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
              <select
                aria-label={m.allUses}
                value={use}
                onChange={(e) => {
                  setUse(e.target.value);
                  setPage(0);
                }}
              >
                <option value="">{m.allUses}</option>
                {Object.keys(COLORS).map((c) => (
                  <option key={c} value={c}>
                    {m[c as Category]}
                  </option>
                ))}
              </select>
            </div>
            <label className="atlas-checkbox">
              <input
                type="checkbox"
                checked={temps}
                onChange={(e) => setTemps(e.target.checked)}
              />
              {m.temporary}
            </label>
            {(detail || feature || detailState !== "ready") && (
              <section className="parcel-inspector" aria-live="polite">
                {detailState !== "ready" ? (
                  <p>
                    {detailState === "loading"
                      ? labels.loading
                      : labels.unavailable}
                  </p>
                ) : (
                  <Inspector
                    detail={detail}
                    feature={feature}
                    context={context}
                    labels={labels}
                    m={m}
                    locale={locale}
                    select={select}
                    parcelCodes={parcelCodes}
                  />
                )}
              </section>
            )}
            {(tab === "future" || tab === "sources") && (
              <>
                {referenceError && (
                  <p role="status">
                    {labels.unavailable}{" "}
                    <button
                      type="button"
                      onClick={() => setAttempt((a) => a + 1)}
                    >
                      {labels.retry}
                    </button>
                  </p>
                )}
                <p className="result-count">
                  {new Intl.NumberFormat(locale).format(referenceItems.length)}{" "}
                  · {m.projectReference}
                </p>
                <References
                  items={referenceItems.slice(
                    currentPage * 40,
                    (currentPage + 1) * 40,
                  )}
                  labels={labels}
                  m={m}
                  locale={locale}
                  choose={(id) => {
                    const f = context?.place.features.find((f) => f.id === id);
                    if (f) choose(f);
                  }}
                />
                <nav className="atlas-pagination" aria-label={labels.sources}>
                  {Array.from(
                    { length: Math.ceil(referenceItems.length / 40) },
                    (_, i) => i + 1,
                  ).map((number) => (
                    <button
                      type="button"
                      key={number}
                      aria-current={
                        currentPage === number - 1 ? "page" : undefined
                      }
                      onClick={() => setPage(number - 1)}
                    >
                      {new Intl.NumberFormat(locale).format(number)}
                    </button>
                  ))}
                </nav>
              </>
            )}
            {tab === "sources" ? (
              <section className="atlas-source-list">
                <p>{m.spatial}</p>
                <a
                  href="https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/0"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  DMT / Onwani · {m.parcels}
                </a>
                {[
                  ...new Map(
                    Object.values(context ?? {}).flatMap((layer) =>
                      layer.features.map(
                        (f) =>
                          [
                            f.properties.source.name,
                            f.properties.source,
                          ] as const,
                      ),
                    ),
                  ).values(),
                ].map((source) => (
                  <article key={source.name}>
                    <h3>
                      <bdi>{source.name}</bdi>
                    </h3>
                    <p>{sourceLabel(source.reliability, m)}</p>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {labels.source} ↗
                    </a>
                    <p>
                      {labels.retrieved} ·{" "}
                      {new Intl.DateTimeFormat(locale, {
                        dateStyle: "medium",
                        timeStyle: "short",
                        timeZone: "Asia/Dubai",
                      }).format(new Date(source.retrieved_at))}
                    </p>
                  </article>
                ))}
              </section>
            ) : tab === "future" ? null : (
              <>
                <p className="result-count" aria-live="polite">
                  {new Intl.NumberFormat(locale).format(count)} · {m[tab]}
                </p>

                {!count && state === "ready" && <p>{m.empty}</p>}
                {tab === "parcels"
                  ? parcelItems
                      .slice(currentPage * 40, (currentPage + 1) * 40)
                      .map((f) => (
                        <button
                          className="atlas-record"
                          type="button"
                          aria-pressed={selected === f.id}
                          key={f.id}
                          onClick={() => void select(f.id)}
                        >
                          <strong>
                            <bdi>
                              {placesByParcel.get(f.id)?.[0] ||
                                f.properties.code}
                            </bdi>
                          </strong>
                          <small>
                            <bdi>
                              {f.properties.code} · {f.properties.land_use}
                            </bdi>
                          </small>
                        </button>
                      ))
                  : mapItems
                      .slice(currentPage * 40, (currentPage + 1) * 40)
                      .map((f) => (
                        <button
                          className="atlas-record"
                          type="button"
                          aria-pressed={feature?.id === f.id}
                          key={f.id}
                          onClick={() => choose(f)}
                        >
                          <strong>
                            <bdi>
                              {f.properties.name ||
                                f.properties.name_ar ||
                                labels.unknown}
                            </bdi>
                          </strong>
                          <small>
                            <bdi>{f.properties.kind}</bdi> ·{" "}
                            {sourceLabel(f.properties.source.reliability, m)}
                          </small>
                        </button>
                      ))}
                <nav className="atlas-pagination" aria-label={labels.list}>
                  {Array.from({ length: maxPage + 1 }, (_, i) => i + 1).map(
                    (number) => (
                      <button
                        type="button"
                        key={number}
                        aria-current={
                          currentPage === number - 1 ? "page" : undefined
                        }
                        onClick={() => setPage(number - 1)}
                      >
                        {new Intl.NumberFormat(locale).format(number)}
                      </button>
                    ),
                  )}
                </nav>
              </>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}
