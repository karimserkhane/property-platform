"use client";

import navigation from "@property-platform/contracts/territories";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { MapLocateButton } from "@/components/map-locate-button";
import { Link } from "@/i18n/navigation";
import { ProjectCover } from "./cover";
import { readProjectData } from "./data";
import { formatHandover, projectPositionQuality } from "./presentation";
import styles from "./project.module.css";
import type { ProjectDetail } from "./types";

// Keep the map selection small. The full, addressable dossier owns its page.
export function ProjectMapSummary({
  slug,
  name,
  developer,
  locale,
  locate,
  locateLabel,
}: {
  slug: string;
  name?: string;
  developer?: string | null;
  locale: string;
  locate?: () => void;
  locateLabel?: string;
}) {
  const t = useTranslations("Project");
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{
    slug: string;
    project: ProjectDetail | null;
    loading: boolean;
  }>({ slug, project: null, loading: true });
  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt retries the same bounded read.
  useEffect(() => {
    const controller = new AbortController();
    setState({ slug, project: null, loading: true });
    void readProjectData(slug, async (path) => {
      const response = await fetch(`/api/atlas/${path}`, {
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(7000)]),
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      return {
        status: response.status,
        data: response.ok ? await response.json() : null,
      };
    }).then((result) => {
      if (!controller.signal.aborted)
        setState({ slug, project: result.project, loading: false });
    });
    return () => controller.abort();
  }, [slug, attempt]);
  const project = state.slug === slug ? state.project : null;
  const quality = project && projectPositionQuality(project.map_locations);
  const loading = state.slug !== slug || state.loading;
  const handover = project?.handover
    ? formatHandover(project.handover, locale, t("quarter"))
    : null;
  const homeTypes = [
    ...new Set(project?.typologies.map((item) => item.property_type) ?? []),
  ];
  const types = new Set([
    "apartment",
    "duplex",
    "penthouse",
    "townhouse",
    "villa",
    "studio",
  ] as const);
  const area = navigation.territories.find(
    (item) => item.id === project?.territory,
  );
  return (
    <article
      className={styles.mapSummary}
      aria-busy={loading}
      data-project-preview={slug}
    >
      <ProjectCover
        project={project}
        compact
        labels={{
          visuals: t("visuals"),
          officialGallery: t("officialGallery"),
          source: t("source"),
          editorialImage: t("editorialImage"),
          previousImage: t("previousImage"),
          nextImage: t("nextImage"),
        }}
      />
      <div className={styles.summaryCopy}>
        <p className={styles.kicker}>{t("project")}</p>
        <h2 lang={project?.language}>
          <bdi>{project?.name ?? name ?? t("project")}</bdi>
        </h2>
        {(project?.developer.name || developer) && (
          <p className={styles.summaryDeveloper}>
            <bdi>{project?.developer.name || developer}</bdi>
          </p>
        )}
        <div className={styles.summaryActions}>
          <Link className={styles.primaryAction} href={`/projects/${slug}`}>
            {t("viewDetails")} <span aria-hidden="true">↗</span>
          </Link>
          {locate && locateLabel && (
            <MapLocateButton label={locateLabel} onClick={locate} />
          )}
        </div>
        {project ? (
          <>
            {!project.map_locations.length && (
              <p className={styles.muted}>{t("notMapped")}</p>
            )}
            {quality && <p className={styles.muted}>{t(quality.label)}</p>}
            <dl className={styles.summaryFacts}>
              {area && (
                <div>
                  <dt>{t("location")}</dt>
                  <dd>
                    <bdi>{locale === "ar" ? area.name_ar : area.name}</bdi>
                  </dd>
                </div>
              )}
              {handover && (
                <div>
                  <dt>{t("handover")}</dt>
                  <dd>{handover}</dd>
                </div>
              )}
              {project.programme_total != null && (
                <div>
                  <dt>
                    {t(
                      project.programme_total.basis === "registered"
                        ? "registeredHomes"
                        : "plannedHomes",
                    )}
                  </dt>
                  <dd>
                    {new Intl.NumberFormat(locale).format(
                      project.programme_total.value,
                    )}
                  </dd>
                </div>
              )}
            </dl>
            {!!homeTypes.length && (
              <p className={styles.summaryTypes}>
                {homeTypes.slice(0, 3).map((type) => (
                  <span className={styles.typeChip} key={type}>
                    {types.has(type as "apartment")
                      ? t(type as "apartment")
                      : type}
                  </span>
                ))}
                {homeTypes.length > 3 && <span aria-hidden="true">…</span>}
              </p>
            )}
          </>
        ) : (
          <p role="status">{loading ? t("loading") : t("unavailable")}</p>
        )}
        {!loading && !project && (
          <button
            type="button"
            onClick={() => setAttempt((value) => value + 1)}
          >
            {t("retry")}
          </button>
        )}
      </div>
    </article>
  );
}
