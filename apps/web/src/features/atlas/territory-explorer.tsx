"use client";

import { useEffect, useState } from "react";
import { Link } from "@/i18n/navigation";
import { Explorer } from "./explorer";
import type {
  AtlasLabels,
  CoverageLabels,
  MapLabels,
  Territory,
  TerritoryRegistry,
} from "./types";

export function TerritoryExplorer({
  labels,
  mapLabels,
  coverage,
  locale,
}: {
  labels: AtlasLabels;
  mapLabels: MapLabels;
  coverage: CoverageLabels;
  locale: string;
}) {
  const [registry, setRegistry] = useState<TerritoryRegistry | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt explicitly retries the registry request.
  useEffect(() => {
    const controller = new AbortController();
    setError(false);
    fetch("/api/atlas/territories", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("unavailable");
        const value = (await response.json()) as TerritoryRegistry;
        setRegistry(value);
        setSelected(
          new URL(window.location.href).searchParams.get("territory") ??
            value.default_territory_id,
        );
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    if (!registry) return;
    const read = () =>
      setSelected(
        new URL(window.location.href).searchParams.get("territory") ??
          registry.default_territory_id,
      );
    window.addEventListener("popstate", read);
    return () => window.removeEventListener("popstate", read);
  }, [registry]);
  const name = (territory: Territory) =>
    locale === "ar" ? territory.name_ar : territory.name;
  function navigate(id: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("territory", id);
    url.searchParams.delete("parcel");
    window.history.pushState(null, "", url);
    setSelected(id);
  }
  if (error || !registry)
    return (
      <main className="explore-shell">
        <h1>{labels.explore}</h1>
        <p role="status">{error ? labels.unavailable : labels.loading}</p>
        {error && (
          <button
            type="button"
            className="button"
            onClick={() => setAttempt((value) => value + 1)}
          >
            {labels.retry}
          </button>
        )}
      </main>
    );
  const territory = registry.territories.find((value) => value.id === selected);
  if (!territory)
    return (
      <main className="explore-shell">
        <h1>{labels.explore}</h1>
        <p role="status">{coverage.unknownArea}</p>
        <button
          type="button"
          className="button"
          onClick={() => navigate(registry.default_territory_id)}
        >
          {coverage.visitPilot}
        </button>
      </main>
    );
  const emirateId =
    territory.level === "emirate" ? territory.id : territory.parent_id;
  const areas = registry.territories.filter(
    (value) => value.parent_id === emirateId && value.level === "area",
  );
  const country = registry.territories.find(
    (value) => value.level === "country",
  );
  const navigation = (
    <div className="territory-controls">
      <label>
        {coverage.emirate}
        <select
          value={emirateId ?? ""}
          onChange={(event) => {
            const first = registry.territories.find(
              (value) =>
                value.parent_id === event.target.value && value.queryable,
            );
            navigate(first?.id ?? event.target.value);
          }}
        >
          <option value="" disabled>
            {coverage.chooseEmirate}
          </option>
          {registry.territories
            .filter((value) => value.level === "emirate")
            .map((value) => (
              <option value={value.id} key={value.id}>
                {name(value)}
              </option>
            ))}
        </select>
      </label>
      {areas.length > 0 && (
        <label>
          {coverage.area}
          <select
            value={territory.level === "area" ? territory.id : ""}
            onChange={(event) => navigate(event.target.value)}
          >
            <option value="" disabled>
              {coverage.area}
            </option>
            {areas.map((value) => (
              <option value={value.id} key={value.id}>
                {name(value)}
              </option>
            ))}
          </select>
        </label>
      )}
      <p>
        {territory.queryable
          ? `${name(territory)} · ${new Intl.NumberFormat(locale).format(territory.parcel_count)} ${mapLabels.parcels}`
          : coverage.preparing}
      </p>
    </div>
  );
  if (!territory.queryable)
    return (
      <main className="explore-shell">
        <div className="explore-heading">
          <h1>{labels.explore}</h1>
          <Link href="/">{labels.back}</Link>
        </div>
        {navigation}
        <section className="coverage-empty">
          <p className="eyebrow">
            <bdi>{name(territory)}</bdi>
          </p>
          <h2>{coverage.preparing}</h2>
          <p>{coverage.preparingBody}</p>
          <button
            type="button"
            className="button"
            onClick={() => navigate(registry.default_territory_id)}
          >
            {coverage.visitPilot}
          </button>
        </section>
      </main>
    );
  return (
    <Explorer
      key={territory.id}
      labels={labels}
      mapLabels={mapLabels}
      locale={locale}
      territory={territory}
      countryBounds={country?.bounds ?? territory.bounds}
      navigation={navigation}
    />
  );
}
