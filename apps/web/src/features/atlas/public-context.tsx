"use client";

import type { components } from "@property-platform/contracts";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { CitedRights } from "@/features/projects/cited-rights";
import styles from "./public-context.module.css";

type Context = components["schemas"]["PublicContextResponse"];
type Dataset = "health" | "schools" | "mobility" | "statistics" | "districts";
const DATASETS: Dataset[] = [
  "health",
  "schools",
  "mobility",
  "statistics",
  "districts",
];

function HistoryNote({
  row,
  locale,
}: {
  row: Pick<
    components["schemas"]["FacilityResponse"],
    "historical" | "retrieved_at" | "field_history"
  >;
  locale: string;
}) {
  const t = useTranslations("Context");
  const dates = [
    ...(row.historical ? [row.retrieved_at] : []),
    ...Object.values(row.field_history).map((field) => field.retrieved_at),
  ];
  if (!dates.length) return null;
  return (
    <small>
      {t("historical")} ·{" "}
      {[...new Set(dates)]
        .map((value) =>
          new Intl.DateTimeFormat(locale, {
            dateStyle: "medium",
            timeZone: "UTC",
          }).format(new Date(value)),
        )
        .join(" · ")}
    </small>
  );
}

export function PublicContext({ locale }: { locale: string }) {
  const t = useTranslations("Context");
  const [dataset, setDataset] = useState<Dataset>("health");
  const [data, setData] = useState<Context | null>(null);
  const [state, setState] = useState("loading");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  // biome-ignore lint/correctness/useExhaustiveDependencies: The retry counter intentionally repeats the request.
  useEffect(() => {
    const controller = new AbortController();
    setState("loading");
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({
          dataset,
          territory: "abu-dhabi",
          q: query,
          offset: String(offset),
        });
        const response = await fetch(`/api/atlas/public-context?${params}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("unavailable");
        const result = (await response.json()) as Context;
        if (!controller.signal.aborted) {
          setData(result);
          setState("ready");
        }
      } catch {
        if (!controller.signal.aborted) setState("error");
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [dataset, query, offset, attempt]);
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 3 });
  const date = (value: string) =>
    new Intl.DateTimeFormat(locale, {
      dateStyle: "medium",
      timeZone: "Asia/Dubai",
    }).format(new Date(value.length === 10 ? `${value}T12:00:00Z` : value));
  return (
    <section className={styles.root}>
      <p className="eyebrow">{t("allEmirate")}</p>
      <h2>{t("title")}</h2>
      <label className="atlas-search">
        <span>{t("selectData")}</span>
        <select
          value={dataset}
          onChange={(e) => {
            setDataset(e.target.value as Dataset);
            setQuery("");
            setOffset(0);
          }}
        >
          {DATASETS.map((key) => (
            <option key={key} value={key}>
              {t(key)}
            </option>
          ))}
        </select>
      </label>
      <p className={styles.note}>
        {t(
          dataset === "districts"
            ? "districtScope"
            : dataset === "schools"
              ? "schoolScope"
              : dataset === "mobility"
                ? "mobilityScope"
                : dataset === "statistics"
                  ? "statisticsScope"
                  : "healthScope",
        )}
      </p>
      <label className="atlas-search">
        <span>{t("search")}</span>
        <input
          type="search"
          dir="auto"
          maxLength={80}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOffset(0);
          }}
        />
      </label>
      {state !== "ready" ? (
        <p role="status">
          {t(state === "error" ? "unavailable" : "loading")}
          {state === "error" && (
            <button type="button" onClick={() => setAttempt((a) => a + 1)}>
              {t("retry")}
            </button>
          )}
        </p>
      ) : (
        data && (
          <>
            <p aria-live="polite">
              {number.format(data.total)} · {t(dataset)}
            </p>
            {data.total === 0 && <p>{t("empty")}</p>}
            <div className={styles.cards}>
              {data.districts.map((row) => (
                <article key={row.source_record_id}>
                  <HistoryNote row={row} locale={locale} />
                  <h3
                    dir="auto"
                    lang={locale === "ar" && row.name_ar ? "ar" : "en"}
                  >
                    {locale === "ar" && row.name_ar ? row.name_ar : row.name}
                  </h3>
                  <p>
                    <bdi>
                      {row.municipality} · {row.district_id}
                    </bdi>
                  </p>
                </article>
              ))}
              {data.health.map((row) => (
                <article key={row.source_record_id}>
                  <HistoryNote row={row} locale={locale} />
                  <span className={styles.badge}>
                    {t(row.planned ? "planned" : "existing")}
                  </span>
                  <h3 dir="auto" lang="en">
                    {row.name}
                  </h3>
                  <p dir="auto" lang="en">
                    {row.facility_type}
                    {row.operator && ` · ${row.operator}`}
                  </p>
                  {row.address && (
                    <p dir="auto" lang="en">
                      {row.address}
                    </p>
                  )}
                  <small>
                    <bdi>
                      {row.latitude.toFixed(5)}, {row.longitude.toFixed(5)}
                    </bdi>
                  </small>
                </article>
              ))}
              {data.schools.map((row) => (
                <article key={row.source_record_id}>
                  <HistoryNote row={row} locale={locale} />
                  <h3
                    dir="auto"
                    lang={locale === "ar" && row.name_ar ? "ar" : "en"}
                  >
                    {locale === "ar" && row.name_ar ? row.name_ar : row.name}
                  </h3>
                  <p dir="auto" lang="en">
                    {row.municipality} · {row.district}
                  </p>
                  <p dir="auto" lang="en">
                    {row.grades_original.split("|").join(" · ")}
                  </p>
                  <small>
                    <bdi>ESIS {row.source_record_id}</bdi>
                  </small>
                </article>
              ))}
              {data.mobility.map((row) => (
                <article key={row.source_record_id}>
                  <HistoryNote row={row} locale={locale} />
                  <h3 dir="auto" lang="en">
                    {row.name}
                  </h3>
                  <p dir="auto" lang="en">
                    {row.origin} → {row.destination}
                  </p>
                  <a href={row.timetable_url} target="_blank" rel="noreferrer">
                    {t("timetable")} ↗
                  </a>
                </article>
              ))}
              {data.statistics.map((row) => (
                <article key={row.source_record_id}>
                  <HistoryNote row={row} locale={locale} />
                  <h3 dir="auto" lang="en">
                    {row.name}
                  </h3>
                  <p className={styles.value}>
                    <bdi>
                      {number.format(Number(row.value))}
                      {row.unit === "percent" ? "%" : ""}
                    </bdi>
                  </p>
                  <p dir="auto" lang="en">
                    {row.region} · {row.reference_year}
                  </p>
                </article>
              ))}
            </div>
            <nav className={styles.paging} aria-label={t("pages")}>
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset((x) => Math.max(0, x - 40))}
              >
                {t("previous")}
              </button>
              <button
                type="button"
                disabled={!data.has_more}
                onClick={() => setOffset((x) => x + 40)}
              >
                {t("next")}
              </button>
            </nav>
            <footer className={styles.note}>
              <a href={data.source_url} target="_blank" rel="noreferrer">
                {t("source")} ↗
              </a>
              {data.retrieved_at && (
                <p>
                  {t(
                    data.acquisition_method === "manual_archive_import"
                      ? "archivedAt"
                      : "retrieved",
                  )}{" "}
                  · {date(data.retrieved_at)}
                </p>
              )}
              <p>
                {data.source_modified_date
                  ? `${t("sourceModified")} · ${date(data.source_modified_date)}`
                  : t("unknownDate")}
              </p>
              {data.acquisition_method === "manual_archive_import" && (
                <p>{t("archiveNote")}</p>
              )}
              <CitedRights rights={data.rights} />
            </footer>
          </>
        )
      )}
    </section>
  );
}
