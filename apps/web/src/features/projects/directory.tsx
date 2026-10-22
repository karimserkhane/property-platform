import type { components } from "@property-platform/contracts";
import { UiIcon } from "@/components/ui-icon";
import { Link } from "@/i18n/navigation";
import { projectMapHref } from "./data";
import styles from "./directory.module.css";
import {
  PROJECT_DIRECTORY_PAGE_SIZE,
  projectDirectoryHref,
} from "./directory-navigation";

type DirectoryProject = components["schemas"]["ProjectSummaryResponse"] & {
  areaName: string;
};

type DirectoryLabels = {
  projects: string;
  viewDetails: string;
  searchProjects: string;
  submitSearch: string;
  searchPlaceholder: string;
  clearSearch: string;
  noProjects: string;
  noProjectsHint: string;
  locate: string;
  mapLocationPending: string;
  previous: string;
  next: string;
  pages: string;
};

export function ProjectDirectoryList({
  projects,
  locale,
  hasMore,
  total,
  offset,
  initialQuery,
  territory,
  labels,
}: {
  projects: DirectoryProject[];
  locale: string;
  hasMore: boolean;
  total: number;
  offset: number;
  initialQuery: string;
  territory?: string;
  labels: DirectoryLabels;
}) {
  const numbers = new Intl.NumberFormat(locale);
  const pageHref = (offset: number, query = initialQuery) => ({
    ...projectDirectoryHref({ territory, query, offset }),
    hash: "project-results",
  });
  const pagination = (offset > 0 || hasMore) && (
    <nav className={styles.pagination} aria-label={labels.pages}>
      {offset > 0 && (
        <Link
          href={pageHref(Math.max(0, offset - PROJECT_DIRECTORY_PAGE_SIZE))}
        >
          {labels.previous}
        </Link>
      )}
      {hasMore && (
        <Link href={pageHref(offset + PROJECT_DIRECTORY_PAGE_SIZE)}>
          {labels.next}
        </Link>
      )}
    </nav>
  );

  return (
    <div className={styles.results} id="project-results">
      <search>
        <form
          className={styles.search}
          action={`/${locale}/projects`}
          method="get"
        >
          {territory && (
            <input type="hidden" name="territory" value={territory} />
          )}
          <label htmlFor="project-search">{labels.searchProjects}</label>
          <div className={styles.searchControl}>
            <UiIcon name="search" />
            <input
              id="project-search"
              name="q"
              type="search"
              maxLength={120}
              dir="auto"
              defaultValue={initialQuery}
              placeholder={labels.searchPlaceholder}
              autoComplete="off"
              enterKeyHint="search"
            />
            <button type="submit">{labels.submitSearch}</button>
          </div>
        </form>
      </search>
      {initialQuery && (
        <Link className={styles.clearSearch} href={pageHref(0, "")}>
          {labels.clearSearch}
        </Link>
      )}
      <div className={styles.resultsHeader}>
        <p className={styles.count} role="status" aria-live="polite">
          <strong>
            <bdi dir="ltr">
              {projects.length
                ? `${numbers.format(offset + 1)}–${numbers.format(offset + projects.length)} / ${numbers.format(total)}`
                : numbers.format(total)}
            </bdi>
          </strong>{" "}
          {labels.projects}
        </p>
        {pagination}
      </div>
      {projects.length ? (
        <div className={styles.grid}>
          {projects.map((project) => (
            <article className={styles.card} key={project.id}>
              <Link
                className={styles.projectLink}
                href={`/projects/${project.slug}`}
                aria-label={`${project.name} · ${project.developer.name}`}
              >
                <span className={styles.monogram} aria-hidden="true">
                  {project.name
                    .split(/\s+/)
                    .slice(0, 2)
                    .map((word) => word[0])
                    .join("")}
                </span>
                <div className={styles.copy}>
                  <p className={styles.kicker}>
                    <bdi>{project.areaName}</bdi>
                  </p>
                  <h2>
                    <bdi>{project.name}</bdi>
                  </h2>
                  <p className={styles.developer}>
                    <bdi>{project.developer.name}</bdi>
                  </p>
                </div>
                <span className={styles.arrow} aria-hidden="true">
                  ↗
                </span>
                <span className={styles.action}>{labels.viewDetails}</span>
              </Link>
              {project.has_map_identity ? (
                <Link
                  className={styles.mapLink}
                  href={projectMapHref(project.slug, project.territory)}
                  aria-label={`${labels.locate} · ${project.name}`}
                >
                  {labels.locate} <span aria-hidden="true">↗</span>
                </Link>
              ) : (
                <p className={styles.mapPending}>{labels.mapLocationPending}</p>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>
          <h2>{labels.noProjects}</h2>
          <p>{labels.noProjectsHint}</p>
        </div>
      )}
      {pagination && (
        <div className={styles.bottomPagination}>{pagination}</div>
      )}
    </div>
  );
}
