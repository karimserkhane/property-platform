"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import type { DistrictMapData, DistrictView } from "./district-map";
import { normalized } from "./presentation";
import type {
  AtlasLabels,
  CoverageLabels,
  MapLabels,
  TerritoryRegistry,
} from "./types";

const DistrictMap = dynamic(() => import("./district-map"), { ssr: false });

export function DistrictOverview({
  locale,
  labels,
  coverage,
  mapLabels,
  registry,
  navigate,
}: {
  locale: string;
  labels: AtlasLabels;
  coverage: CoverageLabels;
  mapLabels: MapLabels;
  registry: TerritoryRegistry;
  navigate: (id: string) => void;
}) {
  const contextText = useTranslations("Context");
  const [data, setData] = useState<DistrictMapData | null>(null);
  const [error, setError] = useState(false);
  const [mapError, setMapError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [municipality, setMunicipality] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<DistrictView>({
    token: 0,
    districtId: null,
  });
  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt explicitly retries the data request.
  useEffect(() => {
    const controller = new AbortController();
    setError(false);
    fetch("/api/atlas/district-map", { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error("unavailable");
        setData((await r.json()) as DistrictMapData);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [attempt]);
  const name = (f: DistrictMapData["features"][number]) =>
    locale === "ar" && f.properties.name_ar
      ? f.properties.name_ar
      : f.properties.name;
  const municipalities: Record<string, string> = {
    ADM: coverage.municipalityAbuDhabi,
    AAM: coverage.municipalityAlAin,
    WRM: coverage.municipalityAlDhafra,
  };
  const rows = (data?.features ?? []).filter(
    (f) =>
      (!municipality || f.properties.municipality === municipality) &&
      (!query ||
        normalized(`${f.properties.name} ${f.properties.name_ar}`).includes(
          normalized(query),
        )),
  );
  const chosen = data?.features.find((f) => f.id === selected);
  const number = new Intl.NumberFormat(locale);
  function openArea(id: string) {
    const territory = registry.territories.find(
      (t) => t.id === id && t.queryable,
    );
    if (territory) navigate(territory.id);
  }
  return (
    <section className="district-overview">
      <div className="district-overview-heading">
        <div>
          <p className="eyebrow">{mapLabels.viewIsland}</p>
          <h2>{coverage.districtsTitle}</h2>
        </div>
        <div className="district-quick-links">
          {registry.territories
            .filter((t) => t.parent_id === "abu-dhabi" && t.queryable)
            .map((t) => (
              <button
                className="button"
                key={t.id}
                type="button"
                onClick={() => openArea(t.id)}
              >
                <bdi>{locale === "ar" ? t.name_ar : t.name}</bdi> ↗
              </button>
            ))}
        </div>
      </div>
      <button
        type="button"
        className="button"
        onClick={() =>
          setView((v) => ({ token: v.token + 1, districtId: null }))
        }
      >
        {mapLabels.viewIsland}
      </button>
      <p>{coverage.boundaryOnly}</p>
      {error || !data ? (
        <p role="status">
          {error ? labels.unavailable : contextText("loading")}{" "}
          {error && (
            <button type="button" onClick={() => setAttempt((a) => a + 1)}>
              {labels.retry}
            </button>
          )}
        </p>
      ) : (
        <>
          <div className="district-overview-grid">
            <div>
              {mapError ? (
                <p role="status">{labels.unavailable}</p>
              ) : (
                <DistrictMap
                  key={locale}
                  data={data}
                  locale={locale}
                  selected={selected}
                  onSelect={setSelected}
                  onError={() => setMapError(true)}
                  label={coverage.districtsTitle}
                  mapLabels={mapLabels}
                  view={view}
                />
              )}
              {chosen && (
                <div className="district-selected">
                  <strong dir="auto">{name(chosen)}</strong>
                  <span>
                    {municipalities[chosen.properties.municipality] ??
                      chosen.properties.municipality}
                  </span>
                  <button
                    type="button"
                    className="button"
                    onClick={() =>
                      setView((v) => ({
                        token: v.token + 1,
                        districtId: chosen.id,
                      }))
                    }
                  >
                    {mapLabels.locate}
                  </button>
                  {chosen.properties.explore_territory_id && (
                    <button
                      className="button"
                      type="button"
                      onClick={() =>
                        openArea(
                          chosen.properties.explore_territory_id as string,
                        )
                      }
                    >
                      {coverage.openArea} ↗
                    </button>
                  )}
                </div>
              )}
            </div>
            <aside className="district-directory">
              <label className="atlas-search">
                <span>{coverage.searchDistricts}</span>
                <input
                  type="search"
                  dir="auto"
                  maxLength={80}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </label>
              <label className="atlas-search">
                <span>{coverage.municipality}</span>
                <select
                  value={municipality}
                  onChange={(e) => setMunicipality(e.target.value)}
                >
                  <option value="">{coverage.showAll}</option>
                  {Object.entries(municipalities).map(([id, title]) => (
                    <option key={id} value={id}>
                      {title}
                    </option>
                  ))}
                </select>
              </label>
              <p aria-live="polite">
                {number.format(rows.length)} · {labels.district}
              </p>
              <div className="district-directory-list">
                {rows.map((f) => (
                  <article
                    key={f.id}
                    className={selected === f.id ? "district-row-selected" : ""}
                  >
                    <button
                      type="button"
                      className="district-name"
                      onClick={() => setSelected(f.id)}
                      aria-pressed={selected === f.id}
                    >
                      <bdi>{name(f)}</bdi>
                    </button>
                    <small>
                      {municipalities[f.properties.municipality] ??
                        f.properties.municipality}
                    </small>
                    {f.properties.explore_territory_id && (
                      <button
                        type="button"
                        className="button"
                        onClick={() =>
                          openArea(f.properties.explore_territory_id as string)
                        }
                      >
                        {coverage.openArea} ↗
                      </button>
                    )}
                  </article>
                ))}
                {!rows.length && <p>{labels.empty}</p>}
              </div>
            </aside>
          </div>
          <p className="district-source">
            <a href={data.source_url} target="_blank" rel="noreferrer">
              DMT / Onwani ↗
            </a>
            {data.retrieved_at &&
              ` · ${labels.retrieved}: ${new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "Asia/Dubai" }).format(new Date(data.retrieved_at))}`}
          </p>
        </>
      )}
    </section>
  );
}
