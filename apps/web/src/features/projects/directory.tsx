"use client";

import type { components } from "@property-platform/contracts";
import { useId, useRef, useState } from "react";
import { Link } from "@/i18n/navigation";
import { projectMapHref } from "./data";
import styles from "./project.module.css";

type DirectoryProject = components["schemas"]["ProjectSummaryResponse"] & {
  areaName: string;
};

type DirectoryLabels = {
  projects: string;
  viewDetails: string;
  searchProjects: string;
  searchPlaceholder: string;
  clearSearch: string;
  noProjects: string;
  noProjectsHint: string;
  openPage: string;
};

// Search only presentation fields; it never creates an identity or map match.
function searchable(value: string) {
  return value.normalize("NFKD").replace(/\p{M}/gu, "").toLocaleLowerCase();
}

export function ProjectDirectoryList({
  projects,
  locale,
  hasMore,
  labels,
}: {
  projects: DirectoryProject[];
  locale: string;
  hasMore: boolean;
  labels: DirectoryLabels;
}) {
  const [query, setQuery] = useState("");
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const clearSearch = () => {
    setQuery("");
    inputRef.current?.focus();
  };
  const terms = searchable(query).trim().split(/\s+/).filter(Boolean);
  const visible = terms.length
    ? projects.filter((project) => {
        const value = searchable(`${project.name} ${project.developer.name}`);
        return terms.every((term) => value.includes(term));
      })
    : projects;
  const count = new Intl.NumberFormat(locale).format(visible.length);

  return (
    <div className={styles.directoryResults}>
      <search className={styles.directorySearch}>
        <label htmlFor={inputId}>{labels.searchProjects}</label>
        <div className={styles.searchControl}>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            aria-hidden="true"
          >
            <circle cx="10.5" cy="10.5" r="6.5" />
            <path d="m16 16 4.5 4.5" />
          </svg>
          <input
            id={inputId}
            ref={inputRef}
            type="search"
            maxLength={120}
            dir="auto"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={labels.searchPlaceholder}
            autoComplete="off"
            enterKeyHint="search"
          />
          {query && (
            <button type="button" onClick={clearSearch}>
              {labels.clearSearch}
            </button>
          )}
        </div>
      </search>
      <p className={styles.resultCount} role="status" aria-live="polite">
        <strong>
          {count}
          {hasMore && !terms.length ? "+" : ""}
        </strong>{" "}
        {labels.projects}
      </p>
      {visible.length ? (
        <div className={styles.directoryGrid}>
          {visible.map((project) => (
            <article className={styles.directoryCard} key={project.id}>
              <Link
                className={styles.directoryLink}
                href={projectMapHref(project.slug, project.territory)}
              >
                <span className={styles.directoryMonogram} aria-hidden="true">
                  {project.name
                    .split(/\s+/)
                    .slice(0, 2)
                    .map((word) => word[0])
                    .join("")}
                </span>
                <div className={styles.directoryCardCopy}>
                  <p className={styles.kicker}>
                    <bdi>{project.areaName}</bdi>
                  </p>
                  <h2>
                    <bdi>{project.name}</bdi>
                  </h2>
                  <p className={styles.directoryDeveloper}>
                    <bdi>{project.developer.name}</bdi>
                  </p>
                </div>
                <span className={styles.directoryArrow} aria-hidden="true">
                  ↗
                </span>
                <span className={styles.directoryAction}>
                  {labels.viewDetails}
                </span>
              </Link>
              <Link
                className={styles.directoryPageLink}
                href={`/projects/${project.slug}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {labels.openPage} <span aria-hidden="true">↗</span>
              </Link>
            </article>
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>
          <h2>{labels.noProjects}</h2>
          <p>{labels.noProjectsHint}</p>
          {query && (
            <button
              className={styles.secondaryButton}
              type="button"
              onClick={clearSearch}
            >
              {labels.clearSearch}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
