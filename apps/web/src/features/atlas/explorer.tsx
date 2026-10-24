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
import { ProjectMapSummary } from "@/features/projects/map-summary";
import { buildingViewSelection } from "./building-3d";
import styles from "./explorer.module.css";
import { imagerySelection } from "./imagery-sources";
import { Inspector } from "./inspector";
import { boundsGeometry } from "./map-analysis";
import { MapLegend } from "./map-legend";
import { MapViewControl } from "./map-view-control";
import { AtlasPagination } from "./pagination";
import type { MapOptions, MapView } from "./parcel-map";
import { readParcelIndex } from "./parcel-pages";
import { type Bounds, ParcelCellCache, viewportCells } from "./parcel-viewport";
import {
  csv,
  download,
  parcelPropertyIndex,
  propertyFeatures,
  sourceLabel,
} from "./presentation";
import { PublicContext } from "./public-context";
import { References } from "./references";
import { SelectionPreview } from "./selection-preview";
import type {
  AtlasLabels,
  MapContext,
  MapFeature,
  MapLabels,
  ParcelDetail,
  ParcelIndex,
  ResearchReference,
  Territory,
} from "./types";

const ParcelMap = dynamic(() => import("./parcel-map"), { ssr: false });
type Tab = "properties" | "context" | "sources";
const TABS: Tab[] = ["properties", "context", "sources"];
const EMPTY_PARCELS: ParcelIndex = {
  type: "FeatureCollection",
  features: [],
  truncated: false,
  classification_version: "",
};

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
  const contextLabels = useTranslations("Context");
  const bbox = (territory.collection_bounds ?? territory.bounds).join(",");
  const territoryQuery = encodeURIComponent(territory.id);
  const collectionBounds = (territory.collection_bounds ??
    territory.bounds) as unknown as Bounds;
  const [collection, setCollection] = useState<ParcelIndex | null>(null);
  const [viewport, setViewport] = useState<Bounds | null>(null);
  const [zoomedOut, setZoomedOut] = useState(false);
  const [exportState, setExportState] = useState<"idle" | "reading" | "error">(
    "idle",
  );
  const parcelCells = useRef<ParcelCellCache | null>(null);
  parcelCells.current ??= new ParcelCellCache((cell, signal) =>
    readParcelIndex(cell, territory.id, signal),
  );
  const [context, setContext] = useState<MapContext | null>(null);
  const [contextError, setContextError] = useState(false);
  const [references, setReferences] = useState<ResearchReference[]>([]);
  const [referenceError, setReferenceError] = useState(false);
  const [detail, setDetail] = useState<ParcelDetail | null>(null);
  const [feature, setFeature] = useState<MapFeature | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [use, setUse] = useState("");
  const [tab, setTab] = useState<Tab>("properties");
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
  const [options, setOptions] = useState<MapOptions>(() => ({
    parcels: true,
    streets: true,
    buildings: true,
    places: true,
    commerce: false,
    offshore: false,
    areas: false,
    names: true,
    codes: false,
    pulse: true,
    ...buildingViewSelection(
      typeof window === "undefined"
        ? null
        : new URL(window.location.href).searchParams,
    ),
    ...imagerySelection(
      typeof window === "undefined"
        ? null
        : new URL(window.location.href).searchParams.get("basemap"),
    ),
  }));
  const [view, setView] = useState<MapView>({ kind: "area", token: 0 });
  const requestId = useRef(0);
  const detailRequest = useRef<AbortController | null>(null);
  const root = useRef<HTMLElement>(null);
  const panel = useRef<HTMLElement>(null);
  const inspection = useRef<HTMLElement>(null);
  const mapSection = useRef<HTMLElement>(null);
  const selectionOrigin = useRef<HTMLElement | null>(null);
  // Float the phone controls above the current sheet, including after photos load.
  useEffect(() => {
    const element = panel.current;
    if (!element) return;
    const observer = new ResizeObserver(() => {
      root.current?.style.setProperty(
        "--selection-panel-height",
        `${element.getBoundingClientRect().height}px`,
      );
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (showSelection && (feature?.id || selected || projectSlug)) {
      inspection.current?.focus({ preventScroll: true });
    }
  }, [feature?.id, selected, projectSlug, showSelection]);
  // biome-ignore lint/correctness/useExhaustiveDependencies: select uses only refs and the immutable territory of this keyed explorer; bind browser history once.
  useEffect(() => {
    const readTab = () => {
      const params = new URL(window.location.href).searchParams;
      const value = params.get("tab");
      if (value && TABS.includes(value as Tab)) {
        setTab(value as Tab);
      } else {
        setTab("properties");
      }
      const slug = params.get("project");
      const parcel = params.get("parcel");
      if (parcel && /^[0-9a-f-]{36}$/i.test(parcel)) {
        void select(parcel);
        if (value && TABS.includes(value as Tab)) setTab(value as Tab);
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
  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt retries the same visible cells; the keyed explorer keeps one territory.
  useEffect(() => {
    if (!viewport) return;
    const cells = viewportCells(viewport, collectionBounds);
    setZoomedOut(cells.kind === "too-large");
    if (cells.kind === "too-large") {
      // Keep the rows already drawn; a wider read would exceed the API budget.
      setState((current) => (current === "loading" ? "ready" : current));
      return;
    }
    if (cells.kind === "outside") {
      setCollection(EMPTY_PARCELS);
      setState("ready");
      return;
    }
    const controller = new AbortController();
    setState("loading");
    parcelCells.current
      ?.rows(cells.cells, controller.signal, (rows) => {
        if (!controller.signal.aborted) setCollection(rows);
      })
      .then((data) => {
        if (controller.signal.aborted) return;
        setCollection(data);
        setState("ready");
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        // A failed cell rejects the visible read; cached cells stay for the retry.
        setCollection(null);
        setState("error");
      });
    return () => controller.abort();
  }, [attempt, viewport]);

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
    () => parcelPropertyIndex(context, collection),
    [context, collection],
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
            features: collection.features.filter(
              (f) => !use || f.properties.category === use,
            ),
          }
        : null,
    [collection, use],
  );
  const referenceItems = references;
  const currentPage = Math.min(
    page,
    Math.max(0, Math.ceil(referenceItems.length / 40) - 1),
  );
  const changeTab = useCallback((t: Tab) => {
    setTab(t);
    setPage(0);
    const url = new URL(window.location.href);
    if (t === "properties") url.searchParams.delete("tab");
    else url.searchParams.set("tab", t);
    window.history.replaceState(null, "", url);
  }, []);
  function frame(kind: MapView["kind"]) {
    setView((v) => ({ kind, token: v.token + 1 }));
  }
  function locate() {
    const row = collection?.features.find((f) => f.id === selected);
    const target =
      feature ??
      projectFeature ??
      (row && { geometry: boundsGeometry(row.properties.bounds) });
    if (target)
      setView((v) => ({
        kind: "feature",
        token: v.token + 1,
        feature: target,
      }));
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
      const target = [origin, mapSection.current, panel.current].find(
        (element) => element?.isConnected && element.getClientRects().length,
      );
      target?.focus({ preventScroll: true });
    });
  }, []);
  useEffect(() => {
    if (!showSelection && tab === "properties") return;
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (tab !== "properties") changeTab("properties");
        else closeDetails();
      }
    };
    window.addEventListener("keydown", dismiss);
    return () => window.removeEventListener("keydown", dismiss);
  }, [showSelection, tab, closeDetails, changeTab]);
  // The export reads the whole territory on demand, not only the visible cells.
  async function exportCSV() {
    setExportState("reading");
    let index: ParcelIndex;
    try {
      index = await readParcelIndex(
        bbox,
        territory.id,
        new AbortController().signal,
      );
    } catch {
      setExportState("error");
      return;
    }
    setExportState("idle");
    const rows = [
      [m.parcels, m.areas, m.landUse, m.construction, labels.source],
      ...index.features
        .filter((f) => !use || f.properties.category === use)
        .map((f) => [
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
    <main
      ref={root}
      className={`explore-shell atlas-shell ${styles.experience}`}
    >
      <h1 className={styles.screenReaderOnly}>{labels.explore}</h1>
      <div className={styles.navigation}>{navigation}</div>
      <div
        className={`atlas-workspace ${styles.workspace}`}
        data-has-selection={hasSelection}
        data-show-selection={
          hasSelection && showSelection && tab === "properties"
        }
        data-panel-open={
          tab !== "properties" || (hasSelection && showSelection)
        }
      >
        <section
          ref={mapSection}
          tabIndex={-1}
          className="map-column"
          aria-label={labels.map}
        >
          <div className={styles.mapActions}>
            <details className={styles.tools} name="explore-map-controls">
              <summary aria-label={m.mapTools}>
                <UiIcon name="layers" />
                <span className={styles.controlText}>{m.mapTools}</span>
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
                      aria-label={m[kind === "focus" ? "viewRT4" : "viewNear"]}
                      onClick={() => frame(kind)}
                    >
                      {m[kind === "focus" ? "viewRT4" : "viewNear"]}
                    </button>
                  ))}
                {(
                  [
                    "parcels",
                    "streets",
                    "buildings",
                    "places",
                    "commerce",
                    "offshore",
                    "areas",
                    "names",
                    "codes",
                  ] as const
                ).map((key) => (
                  <button
                    key={key}
                    type="button"
                    aria-label={m[key]}
                    aria-pressed={options[key]}
                    onClick={() =>
                      setOptions((o) => ({ ...o, [key]: !o[key] }))
                    }
                  >
                    {m[key]}
                  </button>
                ))}
                <button
                  type="button"
                  aria-label={m.projectPulse}
                  aria-pressed={options.pulse}
                  onClick={() => setOptions((o) => ({ ...o, pulse: !o.pulse }))}
                >
                  {m.projectPulse}
                </button>
                <button
                  type="button"
                  aria-label={m.exportCSV}
                  aria-busy={exportState === "reading"}
                  disabled={exportState === "reading"}
                  onClick={exportCSV}
                >
                  {m.exportCSV}
                </button>
                {exportState === "error" && (
                  <p role="status" className={styles.toolNote}>
                    {labels.unavailable}
                  </p>
                )}
                <button
                  type="button"
                  aria-label={m.exportPNG}
                  disabled={
                    state !== "ready" || !context || contextError || mapFailed
                  }
                  onClick={() => frame("export")}
                >
                  {m.exportPNG}
                </button>
                <p className={styles.toolNote}>{m.exploreHint}</p>
              </fieldset>
            </details>
          </div>
          <div className={styles.viewDock}>
            <MapViewControl
              satellite={options.satellite}
              scene={options.scene}
              buildingView={options}
              onBuildingViewChange={(change) => {
                setOptions((value) => ({
                  ...value,
                  ...change,
                  buildings: true,
                }));
                const url = new URL(window.location.href);
                url.searchParams.set("view", change.dimension);
                url.searchParams.set("buildings3d", change.buildingSource);
                url.searchParams.set(
                  "estimates",
                  change.estimatedHeights ? "on" : "off",
                );
                window.history.replaceState(null, "", url);
              }}
              m={m}
              sourceLabel={labels.source}
              locale={locale}
              onChange={(satellite, scene) => {
                setOptions((value) => ({ ...value, satellite, scene }));
                const url = new URL(window.location.href);
                url.searchParams.set("basemap", satellite ? scene : "plan");
                window.history.replaceState(null, "", url);
              }}
            />
          </div>
          <div className="map-frame">
            {(filtered || context) && !mapFailed && (
              <ParcelMap
                key={locale}
                data={filtered ?? EMPTY_PARCELS}
                context={context}
                selected={selected}
                activeFeature={feature ?? projectFeature}
                selectionPanel={panel}
                selectionVisible={
                  hasSelection && showSelection && tab === "properties"
                }
                onSelect={select}
                onFeature={choose}
                onContext={closeDetails}
                onError={() => setMapFailed(true)}
                onViewport={setViewport}
                label={labels.map}
                options={options}
                view={view}
                locale={locale}
                m={m}
                territory={territory}
                countryBounds={countryBounds}
              />
            )}
            {((state !== "ready" && !context) || mapFailed) && (
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
            <MapLegend
              className={styles.legend}
              m={m}
              context={context}
              options={options}
              use={use}
              onUseChange={(value) => {
                setUse(value);
                setPage(0);
              }}
            />
          </div>
          <p className={`map-credit ${styles.screenReaderOnly}`}>
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
          {(contextError || (state === "error" && context)) && (
            <p role="status" className={styles.dataNotice}>
              {labels.unavailable}{" "}
              <button type="button" onClick={() => setAttempt((v) => v + 1)}>
                {labels.retry}
              </button>
            </p>
          )}
          {(collection?.truncated ||
            zoomedOut ||
            Object.values(context ?? {}).some((layer) => layer.truncated)) && (
            <p role="status" className={styles.dataNotice}>
              {labels.truncated}
            </p>
          )}
        </section>
        <aside className="atlas-sidebar" aria-label={labels.select}>
          <section
            id="atlas-panel"
            ref={panel}
            tabIndex={-1}
            aria-label={
              tab === "context"
                ? contextLabels("tab")
                : tab === "sources"
                  ? labels.sources
                  : m[tab]
            }
            className="atlas-panel"
          >
            {tab !== "properties" && (
              <button
                className={styles.panelClose}
                type="button"
                aria-label={m.closeDetails}
                onClick={() => {
                  changeTab("properties");
                  mapSection.current?.focus({ preventScroll: true });
                }}
              >
                <UiIcon name="close" />
              </button>
            )}
            {tab === "context" ? (
              <PublicContext locale={locale} />
            ) : (
              <>
                {tab === "properties" &&
                  showSelection &&
                  (detail ||
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
                        <div className={styles.selectionState} role="status">
                          <p>
                            {detailState === "loading"
                              ? labels.loading
                              : labels.unavailable}
                          </p>
                          {detailState === "error" && selected && (
                            <button
                              className="button"
                              type="button"
                              onClick={() => void select(selected)}
                            >
                              {labels.retry}
                            </button>
                          )}
                        </div>
                      ) : projectSlug ? (
                        <ProjectMapSummary
                          key={projectSlug}
                          slug={projectSlug}
                          locale={locale}
                          locate={projectFeature ? locate : undefined}
                          locateLabel={m.locate}
                        />
                      ) : (
                        <SelectionPreview
                          key={detail?.id ?? feature?.id}
                          detail={detail}
                          feature={feature}
                          labels={labels}
                          m={m}
                          locale={locale}
                          parcelProperties={parcelProperties}
                          locate={locate}
                        >
                          <Inspector
                            showIdentity={false}
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
                            territory={territory.id}
                          />
                        </SelectionPreview>
                      )}
                    </section>
                  )}
                {tab === "sources" && (
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
                ) : null}
              </>
            )}
          </section>
        </aside>
      </div>
    </main>
  );
}
