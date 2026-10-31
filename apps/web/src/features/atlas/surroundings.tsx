"use client";

import type { components } from "@property-platform/contracts";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { CitedRights } from "@/features/projects/cited-rights";
import type { AtlasLabels, MapLabels } from "./types";

type Data = components["schemas"]["Surroundings"];

// Fetch only when requested, for an existing identity; never accept a remote URL.
export function Surroundings({
  identity,
  target,
  territory,
  m,
  labels,
  locale,
}: {
  identity: string;
  target: "parcel" | "building" | "place" | "street";
  territory: string;
  m: MapLabels;
  labels: AtlasLabels;
  locale: string;
}) {
  const usage = useTranslations("Use");
  const [open, setOpen] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const key = `${territory}/${target}/${identity}`;
  const [state, setState] = useState<{
    key: string;
    data: Data | null;
    loading: boolean;
  }>({ key, data: null, loading: false });
  // biome-ignore lint/correctness/useExhaustiveDependencies: state is a per-identity cache; attempt explicitly retries.
  useEffect(() => {
    if (!open || (state.key === key && state.data)) return;
    const controller = new AbortController();
    setState({ key, data: null, loading: true });
    fetch(
      `/api/atlas/surroundings/${target}/${identity}?territory=${encodeURIComponent(territory)}`,
      {
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(8000)]),
        cache: "no-store",
      },
    )
      .then(async (response) => {
        if (!response.ok) throw new Error("unavailable");
        const data = (await response.json()) as Data;
        if (!controller.signal.aborted) setState({ key, data, loading: false });
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setState({ key, data: null, loading: false });
      });
    return () => controller.abort();
  }, [open, key, identity, target, territory, attempt]);
  const data = state.key === key ? state.data : null;
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  return (
    <details
      className="property-proof neighbourhood-proof"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>{m.nearbyPlaces}</summary>
      {open && (
        <>
          <p className="small-text">{m.nearbyNote}</p>
          {!data ? (
            <div role="status">
              <p>
                {state.loading || state.key !== key
                  ? labels.loading
                  : labels.unavailable}
              </p>
              {!state.loading && (
                <button
                  type="button"
                  onClick={() => setAttempt((value) => value + 1)}
                >
                  {labels.retry}
                </button>
              )}
            </div>
          ) : (
            <>
              {!data.groups.length && <p>{m.nearbyEmpty}</p>}
              <div className="amenity-groups">
                {data.groups.map((group) => (
                  <section key={group.key}>
                    <h3>
                      {
                        m[
                          group.key === "worship"
                            ? "nearbyWorship"
                            : group.key === "dining"
                              ? "nearbyDining"
                              : group.key === "transport"
                                ? "nearbyTransport"
                                : group.key === "health"
                                  ? "nearbyHealth"
                                  : group.key === "shopping"
                                    ? "nearbyShopping"
                                    : group.key === "leisure"
                                      ? "nearbyLeisure"
                                      : "nearbyEducation"
                        ]
                      }
                    </h3>
                    <ul>
                      {group.items.map((item) => (
                        <li key={item.id}>
                          <a
                            href={item.source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title={`${item.source.name} · ${new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "Asia/Dubai" }).format(new Date(item.source.retrieved_at))}`}
                          >
                            <bdi>
                              {(locale === "ar" && item.name_ar) ||
                                item.name ||
                                item.name_ar ||
                                (item.use_types[0]
                                  ? usage(item.use_types[0])
                                  : labels.unknown)}
                            </bdi>{" "}
                            ↗
                          </a>
                          <span>
                            ≈ <bdi>{number.format(item.distance_m)}</bdi> m
                          </span>
                          <CitedRights rights={item.source.rights} />
                        </li>
                      ))}
                    </ul>
                  </section>
                ))}
              </div>
              {data.truncated && (
                <p className="small-text">{labels.truncated}</p>
              )}
            </>
          )}
        </>
      )}
    </details>
  );
}
