"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { Link } from "@/i18n/navigation";
import type { AtlasLabels, ParcelCollection, ParcelDetail } from "./types";

const ParcelMap = dynamic(() => import("./parcel-map"), { ssr: false });
const REEM = "54.385,24.465,54.445,24.530";

export function Explorer({
  labels,
  locale,
}: {
  labels: AtlasLabels;
  locale: string;
}) {
  const [collection, setCollection] = useState<ParcelCollection | null>(null);
  const [detail, setDetail] = useState<ParcelDetail | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [detailState, setDetailState] = useState<"loading" | "ready" | "error">(
    "ready",
  );
  const [mapFailed, setMapFailed] = useState(false);
  const requestId = useRef(0);

  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt intentionally retries the same read after a failure.
  useEffect(() => {
    const controller = new AbortController();
    setState("loading");
    setCollection(null);
    fetch(`/api/atlas/parcels?bbox=${REEM}&q=${encodeURIComponent(search)}`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("unavailable");
        const data = (await response.json()) as ParcelCollection;
        if (!Array.isArray(data.features)) throw new Error("invalid response");
        setCollection(data);
        setState("ready");
      })
      .catch(() => {
        if (!controller.signal.aborted) setState("error");
      });
    return () => controller.abort();
  }, [search, attempt]);

  async function select(id: string) {
    const current = ++requestId.current;
    setSelected(id);
    setDetail(null);
    setDetailState("loading");
    const url = new URL(window.location.href);
    url.searchParams.set("parcel", id);
    window.history.replaceState(null, "", url);
    try {
      const response = await fetch(`/api/atlas/parcels/${id}`, {
        signal: AbortSignal.timeout(6000),
      });
      if (!response.ok) throw new Error("unavailable");
      const data = (await response.json()) as ParcelDetail;
      if (current === requestId.current) {
        setDetail(data);
        setDetailState("ready");
      }
    } catch {
      if (current === requestId.current) setDetailState("error");
    }
  }

  const initialSelection = useRef(false);
  useEffect(() => {
    if (initialSelection.current) return;
    initialSelection.current = true;
    const id = new URL(window.location.href).searchParams.get("parcel");
    if (id && /^[0-9a-f-]{36}$/i.test(id)) void select(id);
  });

  const date = (value: string | null) =>
    value
      ? new Intl.DateTimeFormat(locale, {
          dateStyle: "medium",
          timeStyle: "short",
          timeZone: "Asia/Dubai",
        }).format(new Date(value))
      : labels.unknown;
  const pageCount = Math.ceil((collection?.features.length ?? 0) / 50);
  const currentPage = Math.min(page, Math.max(0, pageCount - 1));
  return (
    <main className="explore-shell">
      <div className="explore-heading">
        <div>
          <p className="eyebrow">{labels.pilot}</p>
          <h1>{labels.explore}</h1>
        </div>
        <Link className="text-link" href="/">
          {labels.back}
        </Link>
      </div>
      <form
        className="search-form"
        onSubmit={(event) => {
          event.preventDefault();
          setSearch(query.trim());
        }}
      >
        <label htmlFor="parcel-search">{labels.reference}</label>
        <input
          id="parcel-search"
          value={query}
          maxLength={80}
          onChange={(event) => setQuery(event.target.value)}
          autoComplete="off"
          dir="auto"
        />
        <button className="button" type="submit">
          {labels.search}
        </button>
      </form>
      <p className="notice">{labels.limitations}</p>
      <div className="explore-grid">
        <section className="map-column" aria-label={labels.map}>
          <div className="map-frame">
            {collection && !mapFailed && (
              <ParcelMap
                data={collection}
                selected={selected}
                onSelect={select}
                onError={() => setMapFailed(true)}
                label={labels.map}
              />
            )}
            {(state === "loading" || state === "error" || mapFailed) && (
              <div className="map-status" role="status">
                <p>
                  {state === "loading" ? labels.loading : labels.unavailable}
                </p>
                {state === "error" && (
                  <button
                    type="button"
                    className="button"
                    onClick={() => setAttempt((value) => value + 1)}
                  >
                    {labels.retry}
                  </button>
                )}
              </div>
            )}
          </div>
          <p aria-live="polite">
            {state === "ready" &&
              collection &&
              `${new Intl.NumberFormat(locale).format(collection.features.length)} · ${labels.count}`}
          </p>
          {collection?.truncated && <p role="status">{labels.truncated}</p>}
        </section>
        <aside
          className="parcel-panel"
          aria-label={labels.select}
          aria-live="polite"
        >
          <p className="eyebrow">{labels.pilot}</p>
          <h2>{detail?.code || labels.select}</h2>
          {detailState === "loading" && <p>{labels.loading}</p>}
          {detailState === "error" && <p>{labels.unavailable}</p>}
          {detail && (
            <>
              <dl>
                <dt>{labels.district}</dt>
                <dd>{detail.district || labels.unknown}</dd>
                <dt>{labels.community}</dt>
                <dd>{detail.community || labels.unknown}</dd>
                <dt>{labels.retrieved}</dt>
                <dd>{date(detail.source.retrieved_at)}</dd>
                <dt>{labels.published}</dt>
                <dd>{date(detail.source.published_at)}</dd>
              </dl>
              <a
                className="text-link"
                href={detail.source.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {labels.source} ↗
              </a>
              <p className="small-text">{detail.source.name}</p>
            </>
          )}
        </aside>
      </div>
      <section className="parcel-list" aria-labelledby="list-title">
        <h2 id="list-title">{labels.list}</h2>
        {state === "ready" && collection?.features.length === 0 && (
          <p>{labels.empty}</p>
        )}
        <div className="parcel-buttons">
          {collection?.features
            .slice(currentPage * 50, (currentPage + 1) * 50)
            .map((feature) => (
              <button
                type="button"
                key={feature.id}
                aria-pressed={selected === feature.properties.id}
                onClick={() => void select(feature.properties.id)}
              >
                <bdi>{feature.properties.code || feature.properties.id}</bdi>
              </button>
            ))}
        </div>
        <nav className="parcel-buttons" aria-label={labels.list}>
          {Array.from({ length: pageCount }, (_, index) => index + 1).map(
            (pageNumber) => (
              <button
                type="button"
                key={pageNumber}
                aria-current={
                  currentPage === pageNumber - 1 ? "page" : undefined
                }
                onClick={() => setPage(pageNumber - 1)}
              >
                {new Intl.NumberFormat(locale).format(pageNumber)}
              </button>
            ),
          )}
        </nav>
      </section>
    </main>
  );
}
