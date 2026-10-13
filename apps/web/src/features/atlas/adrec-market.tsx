"use client";

import type { components } from "@property-platform/contracts";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import styles from "./adrec-market.module.css";

type Market = components["schemas"]["AdrecMarketResponse"];

export function AdrecMarket({
  territory,
  locale,
}: {
  territory: string;
  locale: string;
}) {
  const t = useTranslations("Market");
  const [data, setData] = useState<Market | null>(null);
  const [state, setState] = useState("loading");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  // biome-ignore lint/correctness/useExhaustiveDependencies: An explicit retry restarts this request.
  useEffect(() => {
    const controller = new AbortController();
    setState("loading");
    const timer = setTimeout(async () => {
      try {
        const search = new URLSearchParams({
          territory,
          q: query,
          offset: String(offset),
        });
        const response = await fetch(`/api/atlas/adrec-market?${search}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Market unavailable");
        const result = (await response.json()) as Market;
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
  }, [territory, query, offset, attempt]);
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "AED",
    maximumFractionDigits: 2,
  });
  const date = (value: string) =>
    new Intl.DateTimeFormat(locale, {
      dateStyle: "medium",
      timeZone: "UTC",
    }).format(new Date(`${value}T12:00:00Z`));
  return (
    <section className={styles.root}>
      <h2>{t("title")}</h2>
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
            <p className="small-text">
              {data.period_start && data.period_end
                ? `${date(data.period_start)} – ${date(data.period_end)}`
                : t("empty")}
            </p>
            <p className="result-count">
              {number.format(data.total)} · {t("sales")}
            </p>
            <p className="small-text">{t("note")}</p>
            {data.sales.map((row) => (
              <article
                className={styles.sale}
                key={`${data.snapshot_id}:${row.position}`}
              >
                <h3>
                  <bdi>{row.project_name || row.district}</bdi>
                </h3>
                <strong>
                  {row.price_aed === null
                    ? "—"
                    : money.format(Number(row.price_aed))}
                </strong>
                <p>
                  <bdi>
                    {[
                      row.property_type,
                      row.property_layout,
                      row.sale_application_type,
                      row.sale_sequence,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </bdi>
                </p>
                <dl>
                  <div>
                    <dt>{t("date")}</dt>
                    <dd>{date(row.registration_date)}</dd>
                  </div>
                  <div>
                    <dt>{t("area")}</dt>
                    <dd>
                      {row.sold_area_sqm === null
                        ? "—"
                        : `${number.format(Number(row.sold_area_sqm))} m²`}
                    </dd>
                  </div>
                  <div>
                    <dt>{t("share")}</dt>
                    <dd>
                      {row.sold_share === null
                        ? "—"
                        : new Intl.NumberFormat(locale, {
                            style: "percent",
                            maximumFractionDigits: 2,
                          }).format(Number(row.sold_share))}
                    </dd>
                  </div>
                </dl>
              </article>
            ))}
            <nav className="atlas-pagination" aria-label={t("sales")}>
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 40))}
              >
                {t("previous")}
              </button>
              <button
                type="button"
                disabled={!data.has_more}
                onClick={() => setOffset(offset + 40)}
              >
                {t("next")}
              </button>
            </nav>
            {data.indices.length > 0 && (
              <section className={styles.indices}>
                <h3>{t("indices")}</h3>
                <p className="small-text">{t("indexScope")}</p>
                {data.indices.map((row) => (
                  <p key={`${row.kind}:${row.property_type}`}>
                    <bdi>{row.property_type}</bdi>
                    <br />
                    <strong>
                      {row.index_value === null
                        ? "—"
                        : number.format(Number(row.index_value))}
                    </strong>{" "}
                    · {date(row.period_end)}
                  </p>
                ))}
              </section>
            )}
            {data.index_review_needed && (
              <p className="small-text">{t("review")}</p>
            )}
            <p className="small-text">
              <a
                href={data.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                ADREC ↗
              </a>
              {data.retrieved_at && (
                <>
                  {" "}
                  · {t("retrieved")}{" "}
                  {new Intl.DateTimeFormat(locale, {
                    dateStyle: "short",
                    timeStyle: "short",
                    timeZone: "Asia/Dubai",
                  }).format(new Date(data.retrieved_at))}
                </>
              )}
            </p>
          </>
        )
      )}
    </section>
  );
}
