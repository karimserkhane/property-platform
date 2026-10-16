"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { UiIcon } from "@/components/ui-icon";
import { isProjectSlug } from "@/features/projects/data";
import { ProjectMapDossier } from "@/features/projects/map-dossier";
import { Link } from "@/i18n/navigation";
import { AdrecMarket } from "./adrec-market";
import styles from "./explorer.module.css";
import { Inspector } from "./inspector";
import { AtlasPagination } from "./pagination";
import type { MapOptions, MapView } from "./parcel-map";
import { readParcelPages } from "./parcel-pages";
import {
  type Category,
  COLORS,
  csv,
  download,
  normalized,
  parcelPropertyIndex,
  preferredParcelProperty,
  propertyFeatures,
  propertyName,
  readableParcelCode,
  sourceLabel,
} from "./presentation";
import { PublicContext } from "./public-context";
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
  Territory,
} from "./types";

const ParcelMap = dynamic(() => import("./parcel-map"), { ssr: false });
type Tab =
  | "properties"
  | "parcels"
  | "places"
  | "streets"
  | "buildings"
  | "future"
  | "sources"
  | "market"
  | "context";
const TABS: Tab[] = [
  "properties",
  "market",
  "context",
  "places",
  "buildings",
  "streets",
  "parcels",
  "future",
  "sources",
];

export function Explorer({
  labels,
  mapLabels: m,
  locale,
  territory,
  countryBounds,
  navigation,
}: {
  labels: AtlasLabels;
  mapLabels: MapLabels;
  locale: string;
  territory: Territory;
  countryBounds: number[];
  navigation: ReactNode;
}) {
  const marketLabels = useTranslations("Market");
  const contextLabels = useTranslations("Context");
  const usageLabels = useTranslations("Use");
  const bbox = (territory.collection_bounds ?? territory.bounds).join(",");
  const territoryQuery = encodeURIComponent(territory.id);
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
  const [tab, setTab] = useState<Tab>("properties");
  const [mobileView, setMobileView] = useState<"map" | "list">("map");
  const [showSelection, setShowSelection] = useState(false);
  const [projectSlug, setProjectSlug] = useState<string | null>(null);
  const hasSelection = Boolean(selected || feature || projectSlug);
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
  const [view, setView] = useState<MapView>({ kind: "area", token: 0 });
  const requestId = useRef(0);
  const detailRequest = useRef<AbortController | null>(null);
  const panel = useRef<HTMLElement>(null);
  const inspection = useRef<HTMLElement>(null);
  const mapSection = useRef<HTMLElement>(null);
  const mapViewButton = useRef<HTMLButtonElement>(null);
  const selectionOrigin = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (showSelection && (feature?.id || selected || projectSlug)) {
      inspection.current?.focus({ preventScroll: true });
      if (selectionOrigin.current && selectionOrigin.current.tagName !== "BODY")
        inspection.current?.scrollIntoView({
          block: "start",
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
            .matches
            ? "instant"
            : "smooth",
        });
    }
  }, [feature?.id, selected, projectSlug, showSelection]);
  // biome-ignore lint/correctness/useExhaustiveDependencies: select uses only refs and the immutable territory of this keyed explorer; bind browser history once.
  useEffect(() => {
    const readTab = () => {
      const params = new URL(window.location.href).searchParams;
      const value = params.get("tab");
      if (value && TABS.includes(value as Tab)) {
        setTab(value as Tab);
        setMobileView("list");
      } else {
        setTab("properties");
      }
      const slug = params.get("project");
      const parcel = params.get("parcel");
      if (parcel && /^[0-9a-f-]{36}$/i.test(parcel)) {
        void select(parcel);
        return;
      }
      detailRequest.current?.abort();
      ++requestId.current;
      setFeature(null);
      setSelected(null);
      setDetail(null);
      setDetailState("ready");
      if (slug && !params.has("parcel") && isProjectSlug(slug)) {
        setProjectSlug(slug);
        setShowSelection(true);

        setTab("properties");
        setMobileView("map");
      } else {
        setProjectSlug(null);
        setShowSelection(false);
      }
    };
    readTab();
    window.addEventListener("popstate", readTab);
    return () => window.removeEventListener("popstate", readTab);
  }, []);
  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt retries the same bounded read.
  useEffect(() => {
    const controller = new AbortController();
    setState("loading");
    setContextError(false);
    setReferenceError(false);
    fetch(`/api/atlas/references?territory=${territoryQuery}`, {
      signal: controller.signal,
    })
      .then(async (r) => {
        if (!r.ok) throw new Error("unavailable");
        setReferences(await r.json());
      })
      .catch(() => {
        if (!controller.signal.aborted) setReferenceError(true);
      });
    readParcelPages(bbox, territory.id, controller.signal)
      .then((data) => {
        setCollection(data);
        setState("ready");
      })
      .catch(() => {
        if (!controller.signal.aborted) setState("error");
      });
    fetch(`/api/atlas/map-context?bbox=${bbox}&territory=${territoryQuery}`, {
      signal: controller.signal,
    })
      .then(async (r) => {
        if (!r.ok) throw new Error("unavailable");
        setContext((await r.json()) as MapContext);
      })
      .catch(() => {
        if (!controller.signal.aborted) setContextError(true);
      });
    return () => controller.abort();
  }, [attempt, bbox, territoryQuery, territory.id]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt retries a failed bounded read; immutable previews stay loaded.
  useEffect(() => {
    if (!options.satellite || imagery.length) return;
    const controller = new AbortController();
    fetch(`/api/atlas/imagery?territory=${territoryQuery}`, {
      signal: controller.signal,
    })
      .then(async (r) => {
        if (!r.ok) throw new Error("unavailable");
        setImagery(await r.json());
      })
      .catch(() => {
        if (!controller.signal.aborted) setContextError(true);
      });
    return () => controller.abort();
  }, [options.satellite, imagery.length, attempt, territoryQuery]);

  async function select(id: string) {
    selectionOrigin.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    setTab("properties");
    setShowSelection(true);
    setProjectSlug(null);

    detailRequest.current?.abort();
    detailRequest.current = new AbortController();
    const current = ++requestId.current;
    setSelected(id);
    setFeature(null);
    setDetail(null);
    setDetailState("loading");
    const url = new URL(window.location.href);
    url.searchParams.set("parcel", id);
    url.searchParams.delete("tab");
    url.searchParams.delete("project");
    window.history.replaceState(null, "", url);
    try {
      const r = await fetch(
        `/api/atlas/parcels/${id}?territory=${territoryQuery}`,
        {
          signal: AbortSignal.any([
            detailRequest.current.signal,
            AbortSignal.timeout(8000),
          ]),
        },
      );
      if (!r.ok) throw new Error("unavailable");
      const data = (await r.json()) as ParcelDetail;
      if (current === requestId.current) {
        setSelected(data.id);
        if (data.id !== id) {
          const canonicalUrl = new URL(window.location.href);
          canonicalUrl.searchParams.set("parcel", data.id);
          window.history.replaceState(null, "", canonicalUrl);
        }
        setDetail(data);
        setDetailState("ready");
      }
    } catch {
      if (current === requestId.current) setDetailState("error");
    }
  }
  function choose(f: MapFeature) {
    selectionOrigin.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    setTab("properties");
    setShowSelection(true);
    setProjectSlug(null);

    detailRequest.current?.abort();
    ++requestId.current;
    setFeature(f);
    setDetail(null);
    setSelected(null);
    setDetailState("ready");
    const url = new URL(window.location.href);
    url.searchParams.delete("parcel");
    url.searchParams.delete("tab");
    if (f.properties.presentation?.project?.slug)
      url.searchParams.set("project", f.properties.presentation.project.slug);
    else url.searchParams.delete("project");
    window.history.replaceState(null, "", url);
  }
  const parcelProperties = useMemo(
    () => parcelPropertyIndex(context),
    [context],
  );
  // Only existing explicit project links may provide a location or highlight.
  const projectFeature = useMemo(
    () =>
      projectSlug
        ? (propertyFeatures(context).find(
            (item) =>
              item.properties.presentation?.project?.slug === projectSlug,
          ) ?? null)
        : null,
    [context, projectSlug],
  );
  const placesByParcel = useMemo(() => {
    const names = new Map<string, string[]>(
      [...parcelProperties].map(([id, candidates]) => [
        id,
        candidates.flatMap((p) => [
          p.name,
          p.name_ar,
          p.presentation?.name ?? "",
          p.presentation?.developer ?? "",
          p.presentation?.publisher ?? "",
        ]),
      ]),
    );
    for (const f of context?.place.features ?? [])
      for (const id of f.properties.parcel_ids)
        names.set(id, [
          ...(names.get(id) ?? []),
          f.properties.name,
          f.properties.name_ar,
        ]);
    return names;
  }, [context, parcelProperties]);
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
                      ...(p.use_types ?? []).map((type) => usageLabels(type)),
                      ...(placesByParcel.get(p.id) ?? []),
                    ].join(" "),
                  ).includes(normalized(query)))
              );
            }),
          }
        : null,
    [collection, sector, use, temps, query, placesByParcel, usageLabels],
  );
  const target =
    tab === "streets" ? "street" : tab === "buildings" ? "building" : "place";
  const mapItems = (
    tab === "properties"
      ? propertyFeatures(context)
      : (context?.[target].features ?? [])
  ).filter(
    (f) =>
      !query ||
      normalized(
        [
          f.properties.name,
          f.properties.name_ar,
          f.properties.presentation?.name,
          f.properties.presentation?.developer,
          f.properties.presentation?.publisher,
          f.properties.kind,
          ...(f.properties.use_types ?? []).map((type) => usageLabels(type)),
        ].join(" "),
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
    const url = new URL(window.location.href);
    if (t === "properties") url.searchParams.delete("tab");
    else url.searchParams.set("tab", t);
    window.history.replaceState(null, "", url);
  }
  function frame(kind: MapView["kind"]) {
    setMobileView("map");
    setView((v) => ({ kind, token: v.token + 1 }));
  }
  function locate() {
    setMobileView("map");
    setShowSelection(false);
    const target =
      feature ??
      projectFeature ??
      collection?.features.find((f) => f.id === selected);
    if (target)
      setView((v) => ({
        kind: "feature",
        token: v.token + 1,
        feature: target,
      }));
    mapSection.current?.scrollIntoView({
      block: "start",
      behavior: "instant",
    });
    requestAnimationFrame(() =>
      mapSection.current?.focus({ preventScroll: true }),
    );
  }
  const closeDetails = useCallback(() => {
    detailRequest.current?.abort();
    ++requestId.current;
    setFeature(null);
    setDetail(null);
    setSelected(null);
    setProjectSlug(null);

    setDetailState("ready");
    setShowSelection(false);
    const url = new URL(window.location.href);
    url.searchParams.delete("parcel");
    url.searchParams.delete("project");
    window.history.replaceState(null, "", url);
    const origin = selectionOrigin.current;
    requestAnimationFrame(() => {
      const target = [
        origin,
        mapViewButton.current,
        mapSection.current,
        panel.current,
      ].find(
        (element) => element?.isConnected && element.getClientRects().length,
      );
      target?.focus({ preventScroll: true });
    });
  }, []);
  useEffect(() => {
    if (!showSelection) return;
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeDetails();
    };
    window.addEventListener("keydown", dismiss);
    return () => window.removeEventListener("keydown", dismiss);
  }, [showSelection, closeDetails]);
  function exportCSV() {
    const rows = [
      [m.parcels, m.areas, m.landUse, m.construction, labels.source],
      ...(filtered?.features ?? []).map((f) => [
        f.properties.code,
        f.properties.community,
        f.properties.land_use,
        f.properties.construction_status,
        f.properties.source_url ?? "",
      ]),
    ];
    download(
      new Blob(["\uFEFF", csv(rows)], { type: "text/csv;charset=utf-8" }),
      `${territory.id}-parcels.csv`,
    );
  }
  return (
    <main className={`explore-shell atlas-shell ${styles.experience}`}>
      <div className="explore-heading">
        <div>
          <p className="eyebrow">{labels.pilot}</p>
          <h1>{labels.explore}</h1>
        </div>
        <Link className="text-link" href="/">
          {labels.back}
        </Link>
      </div>
      {navigation}
      <div className={styles.discoveryBar}>
        {tab !== "market" && tab !== "context" && (
          <label className={styles.search}>
            <span className="sr-only">{m.searchPrompt}</span>
            <UiIcon name="search" />
            <input
              type="search"
              value={query}
              placeholder={m.searchPrompt}
              maxLength={80}
              dir="auto"
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(0);
              }}
            />
            {query && (
              <button
                type="button"
                aria-label={labels.reset}
                onClick={() => {
                  setQuery("");
                  setPage(0);
                }}
              >
                <UiIcon name="close" />
              </button>
            )}
          </label>
        )}
        <fieldset className={styles.mobileNavigation} aria-label={m.mapView}>
          <button
            type="button"
            ref={mapViewButton}
            aria-pressed={mobileView === "map"}
            onClick={() => {
              setMobileView("map");
              if (hasSelection) changeTab("properties");
            }}
          >
            <UiIcon name="map" />
            {m.mapView}
          </button>
          <button
            type="button"
            aria-pressed={mobileView === "list"}
            onClick={() => setMobileView("list")}
          >
            <UiIcon name="list" />
            {m.listView}
            {state === "ready" && tab !== "market" && tab !== "context" && (
              <span className={styles.count}>
                {new Intl.NumberFormat(locale).format(count)}
              </span>
            )}
          </button>
        </fieldset>
        {hasSelection && (
          <button
            type="button"
            className={styles.selectionReturn}
            onClick={() => {
              setShowSelection(true);
              setMobileView("map");
              changeTab("properties");
              requestAnimationFrame(() => {
                inspection.current?.scrollIntoView({
                  block: "start",
                  behavior: "instant",
                });
                inspection.current?.focus({ preventScroll: true });
              });
            }}
          >
            {m.selectionLabel}
          </button>
        )}
      </div>
      <div
        className={`atlas-workspace ${styles.workspace}`}
        data-mobile-view={mobileView}
        data-has-selection={hasSelection}
        data-show-selection={showSelection && tab === "properties"}
      >
        <section
          ref={mapSection}
          tabIndex={-1}
          className="map-column"
          aria-label={labels.map}
        >
          <div className={styles.mapActions}>
            <button type="button" onClick={() => frame("area")}>
              <UiIcon name="map" />
              {m.viewIsland}
            </button>
            <button
              type="button"
              aria-pressed={options.satellite}
              onClick={() =>
                setOptions((value) => ({
                  ...value,
                  satellite: !value.satellite,
                }))
              }
            >
              {options.satellite ? m.plan : m.satellite}
            </button>
            <details className={styles.tools}>
              <summary>
                <UiIcon name="layers" />
                {m.mapTools}
              </summary>
              <fieldset
                className={`atlas-toolbar ${styles.toolPanel}`}
                aria-label={m.layers}
              >
                {(["focus", "near"] as const)
                  .filter((kind) =>
                    kind === "focus"
                      ? territory.focus_bounds
                      : territory.neighbourhood_bounds,
                  )
                  .map((kind) => (
                    <button
                      key={kind}
                      type="button"
                      onClick={() => frame(kind)}
                    >
                      {m[kind === "focus" ? "viewRT4" : "viewNear"]}
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
                    onClick={() =>
                      setOptions((o) => ({ ...o, [key]: !o[key] }))
                    }
                  >
                    {m[key]}
                  </button>
                ))}
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
            </details>
          </div>
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
                key={locale}
                data={filtered}
                context={context}
                selected={selected}
                activeFeature={feature ?? projectFeature}
                onSelect={select}
                onFeature={choose}
                onError={() => setMapFailed(true)}
                label={labels.map}
                options={options}
                view={view}
                locale={locale}
                imagery={imagery}
                m={m}
                territory={territory}
                countryBounds={countryBounds}
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
            <details className="map-legend" open={tab !== "properties"}>
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
            <bdi>
              {[
                ...new Set(
                  collection?.features
                    .map((item) => item.properties.source_name)
                    .filter(Boolean),
                ),
              ].join(" · ")}
            </bdi>
            {Object.values(context ?? {}).some((layer) =>
              layer.features.some((item) =>
                item.properties.source.name.startsWith("OpenStreetMap"),
              ),
            ) && (
              <>
                {" "}
                ·{" "}
                <a
                  href="https://www.openstreetmap.org/copyright"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  © OpenStreetMap contributors · ODbL
                </a>
              </>
            )}
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
          <fieldset className="atlas-tabs" aria-label={m.dataViews}>
            {TABS.map((t) => (
              <button
                type="button"
                aria-pressed={tab === t}
                aria-controls="atlas-panel"
                id={`tab-${t}`}
                key={t}
                onClick={() => changeTab(t)}
              >
                {t === "context"
                  ? contextLabels("tab")
                  : t === "market"
                    ? marketLabels("tab")
                    : t === "sources"
                      ? labels.sources
                      : m[t]}
              </button>
            ))}
          </fieldset>
          <section
            id="atlas-panel"
            ref={panel}
            aria-label={
              tab === "context"
                ? contextLabels("tab")
                : tab === "market"
                  ? marketLabels("tab")
                  : tab === "sources"
                    ? labels.sources
                    : m[tab]
            }
            className="atlas-panel"
          >
            {tab === "context" ? (
              <PublicContext locale={locale} />
            ) : tab === "market" ? (
              <AdrecMarket
                key={territory.id}
                territory={territory.id}
                locale={locale}
              />
            ) : (
              <>
                {(detail ||
                  feature ||
                  projectSlug ||
                  detailState !== "ready") && (
                  <section
                    ref={inspection}
                    tabIndex={-1}
                    className="parcel-inspector"
                    aria-live="polite"
                  >
                    <div className="property-inspector-controls">
                      <span>{m.selectionLabel}</span>
                      <div className={styles.selectionActions}>
                        <button
                          type="button"
                          aria-label={m.closeDetails}
                          onClick={closeDetails}
                        >
                          <UiIcon name="close" />
                        </button>
                      </div>
                    </div>
                    {detailState !== "ready" ? (
                      <p>
                        {detailState === "loading"
                          ? labels.loading
                          : labels.unavailable}
                      </p>
                    ) : projectSlug ? (
                      <ProjectMapDossier
                        key={projectSlug}
                        slug={projectSlug}
                        locale={locale}
                        locate={projectFeature ? locate : undefined}
                        locateLabel={m.locate}
                      />
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
                        parcelProperties={parcelProperties}
                        references={references}
                        locate={locate}
                        choose={choose}
                      />
                    )}
                  </section>
                )}
                {tab === "parcels" && (
                  <>
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
                  </>
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
                      {new Intl.NumberFormat(locale).format(
                        referenceItems.length,
                      )}{" "}
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
                        const f = context?.place.features.find(
                          (f) => f.id === id,
                        );
                        if (f) choose(f);
                        if (f)
                          setView((v) => ({
                            kind: "feature",
                            token: v.token + 1,
                            feature: f,
                          }));
                      }}
                    />
                    <AtlasPagination
                      page={currentPage}
                      pageCount={Math.ceil(referenceItems.length / 40)}
                      onPageChange={setPage}
                      label={labels.sources}
                      previousLabel={m.previousPage}
                      nextLabel={m.nextPage}
                      locale={locale}
                    />
                  </>
                )}
                {tab === "sources" ? (
                  <section className="atlas-source-list">
                    <p>{m.spatial}</p>
                    {[
                      ...new Set(
                        (collection?.features ?? []).flatMap((item) =>
                          item.properties.source_url
                            ? [item.properties.source_url]
                            : [],
                        ),
                      ),
                    ].map((url) => (
                      <a
                        key={url}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {labels.source} · {m.parcels}
                      </a>
                    ))}
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
                                  {propertyName(
                                    preferredParcelProperty(
                                      parcelProperties.get(f.id) ?? [],
                                      locale,
                                    ) ?? { name: "", name_ar: "", kind: "" },
                                    locale,
                                  ) ||
                                    (f.properties.use_types?.length
                                      ? usageLabels(f.properties.use_types[0])
                                      : f.properties.land_use || m.parcelTitle)}
                                </bdi>
                              </strong>
                              <small>
                                <bdi>
                                  {readableParcelCode(f.properties.code)} ·{" "}
                                  {f.properties.land_use}
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
                                  {propertyName(f.properties, locale) ||
                                    (f.properties.use_types?.length
                                      ? usageLabels(f.properties.use_types[0])
                                      : tab === "properties" ||
                                          tab === "buildings"
                                        ? m.building
                                        : labels.unknown)}
                                </bdi>
                              </strong>
                              <small>
                                {tab === "properties" ? (
                                  <>
                                    {f.properties.use_types?.length
                                      ? f.properties.use_types
                                          .map((type) => usageLabels(type))
                                          .join(" · ")
                                      : f.properties.kind.endsWith(
                                            "_project_marker",
                                          )
                                        ? m.project
                                        : m.building}
                                    {f.properties.presentation?.developer && (
                                      <>
                                        {" "}
                                        ·{" "}
                                        <bdi>
                                          {f.properties.presentation.developer}
                                        </bdi>
                                      </>
                                    )}
                                    {f.properties.levels != null && (
                                      <>
                                        {" "}
                                        ·{" "}
                                        {new Intl.NumberFormat(locale).format(
                                          f.properties.levels,
                                        )}{" "}
                                        {m.levels}
                                      </>
                                    )}
                                  </>
                                ) : (
                                  <>
                                    <bdi>
                                      {f.properties.use_types?.length
                                        ? f.properties.use_types
                                            .map((type) => usageLabels(type))
                                            .join(" · ")
                                        : f.properties.kind}
                                    </bdi>{" "}
                                    ·{" "}
                                    {sourceLabel(
                                      f.properties.source.reliability,
                                      m,
                                    )}
                                  </>
                                )}
                              </small>
                            </button>
                          ))}
                    <AtlasPagination
                      page={currentPage}
                      pageCount={maxPage + 1}
                      onPageChange={setPage}
                      label={m[tab]}
                      previousLabel={m.previousPage}
                      nextLabel={m.nextPage}
                      locale={locale}
                    />
                  </>
                )}
              </>
            )}
          </section>
        </aside>
      </div>
    </main>
  );
}
