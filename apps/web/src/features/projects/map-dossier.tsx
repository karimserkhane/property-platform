"use client";

import { useMessages, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Link } from "@/i18n/navigation";
import { readProjectData } from "./data";
import { ProjectDetailView } from "./detail";
import styles from "./project.module.css";
import type { ProjectDetail, ProjectLabels } from "./types";

export function ProjectMapDossier({
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
  const messages = useMessages();
  const labels = Object.fromEntries(
    Object.keys(messages.Project).map((key) => [
      key,
      t(key as keyof ProjectLabels),
    ]),
  ) as ProjectLabels;
  const root = useRef<HTMLDivElement>(null);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{
    slug: string;
    project: ProjectDetail | null;
    loading: boolean;
  }>({ slug, project: null, loading: true });
  // biome-ignore lint/correctness/useExhaustiveDependencies: attempt retries this fixed, bounded project read.
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
  // Never show the preceding property's dossier while its replacement loads.
  const project = state.slug === slug ? state.project : null;
  const loading = state.slug !== slug || state.loading;
  function section(id: string) {
    const target = root.current?.querySelector<HTMLElement>(`[id="${id}"]`);
    if (!target) return;
    target.scrollIntoView({ block: "start", behavior: "instant" });
    target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
  }
  return (
    <div ref={root} aria-busy={loading} data-project-preview={slug}>
      {project ? (
        <ProjectDetailView
          project={project}
          locale={locale}
          labels={labels}
          variant="map"
          onSectionChange={section}
          onLocate={locate}
          locateLabel={locateLabel}
        />
      ) : (
        <div className={styles.previewCopy}>
          <h2>
            <bdi>{name ?? t("project")}</bdi>
          </h2>
          {developer && (
            <p>
              <bdi>{developer}</bdi>
            </p>
          )}
          <p role="status">{loading ? t("loading") : t("unavailable")}</p>
          {!loading && (
            <>
              <button
                className={styles.secondaryButton}
                type="button"
                onClick={() => setAttempt((value) => value + 1)}
              >
                {t("retry")}
              </button>
              <Link
                className={styles.textAction}
                href={`/projects/${slug}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {t("openPage")}
              </Link>
            </>
          )}
        </div>
      )}
    </div>
  );
}
