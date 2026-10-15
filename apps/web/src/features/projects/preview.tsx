"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Link } from "@/i18n/navigation";
import { ProjectCover } from "./cover";
import { readProjectData } from "./data";
import { formatHandover, projectMedia, safeSourceUrl } from "./presentation";
import styles from "./project.module.css";
import type { ProjectDetail } from "./types";

export function ProjectPreview({
  slug,
  name,
  developer,
  locale,
  locate,
  locateLabel,
}: {
  slug: string;
  name: string;
  developer?: string | null;
  locale: string;
  locate: () => void;
  locateLabel: string;
}) {
  const t = useTranslations("Project");
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{
    slug: string;
    project: ProjectDetail | null;
    loading: boolean;
  }>({ slug, project: null, loading: true });
  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt intentionally starts a fresh request when the visitor retries.
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
  // Old data must never flash under a newly selected property's identity.
  const project = state.slug === slug ? state.project : null;
  const loading = state.slug !== slug || state.loading;
  const handover = project?.handover
    ? formatHandover(project.handover, locale, t("quarter"))
    : null;
  const website = safeSourceUrl(project?.website_url);
  const types = project
    ? [...new Set(project.typologies.map((item) => item.property_type))]
    : [];
  return (
    <article
      className={styles.preview}
      data-project-preview={slug}
      aria-busy={loading}
    >
      {project && (
        <ProjectCover
          key={project.id}
          project={project}
          labels={{
            visuals: t("visuals"),
            officialGallery: t("officialGallery"),
          }}
        />
      )}
      <div className={styles.previewCopy}>
        <p className={styles.kicker}>{t("project")}</p>
        <h2 lang={project?.language} dir="auto">
          <bdi>{project?.name ?? name}</bdi>
        </h2>
        <p className={styles.previewDeveloper}>
          <bdi>{project?.developer.name ?? developer}</bdi>
        </p>
        {loading ? (
          <p className={styles.muted} role="status">
            {t("loading")}
          </p>
        ) : project ? (
          <>
            <div className={styles.previewFacts}>
              <div>
                <span>{t("handover")}</span>
                <strong>{handover ?? t("notDocumented")}</strong>
              </div>
              <div>
                <span>{t("plannedHomes")}</span>
                <strong>
                  {project.programme_total
                    ? new Intl.NumberFormat(locale).format(
                        project.programme_total.value,
                      )
                    : t("notDocumented")}
                </strong>
              </div>
            </div>
            {types.length > 0 && (
              <div className={styles.chips}>
                {types.map((type) => (
                  <span key={type}>
                    {[
                      "apartment",
                      "duplex",
                      "penthouse",
                      "townhouse",
                      "villa",
                      "studio",
                    ].includes(type) ? (
                      t(type as "apartment")
                    ) : (
                      <bdi>{type}</bdi>
                    )}
                  </span>
                ))}
              </div>
            )}
            {project.amenities.length > 0 && (
              <p
                className={styles.previewAmenities}
                lang={project.language}
                dir="auto"
              >
                {project.amenities
                  .slice(0, 3)
                  .map((item) => item.label)
                  .join(" · ")}
              </p>
            )}
            {projectMedia(project).documents.length > 0 && (
              <Link
                className={styles.textAction}
                href={`/projects/${slug}#project-documents`}
              >
                {t("documents")} <span aria-hidden="true">↗</span>
              </Link>
            )}
          </>
        ) : (
          <div role="status">
            <p className={styles.muted}>{t("unavailable")}</p>
            <button
              className={styles.secondaryButton}
              type="button"
              onClick={() => setAttempt((value) => value + 1)}
            >
              {t("retry")}
            </button>
          </div>
        )}
        <Link className={styles.primaryAction} href={`/projects/${slug}`}>
          {t("viewDetails")} <span aria-hidden="true">↗</span>
        </Link>
        <div className={styles.previewActions}>
          {website && (
            <a href={website} target="_blank" rel="noopener noreferrer">
              {t("developerWebsite")} ↗
            </a>
          )}
          <button
            className={styles.secondaryButton}
            type="button"
            onClick={locate}
          >
            {locateLabel}
          </button>
        </div>
      </div>
    </article>
  );
}
