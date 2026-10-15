"use client";

import { useState } from "react";
import { approvedDelivery, projectMedia, safeSourceUrl } from "./presentation";
import styles from "./project.module.css";
import type { ProjectDetail, ProjectLabels } from "./types";

export function ProjectCover({
  project,
  labels,
}: {
  project: ProjectDetail;
  labels: Pick<ProjectLabels, "visuals" | "officialGallery">;
}) {
  const { hero } = projectMedia(project);
  const [failed, setFailed] = useState<string | null>(null);
  const delivery = hero && approvedDelivery(hero);
  const website = safeSourceUrl(project.website_url);
  const licence = safeSourceUrl(hero?.licence_url);
  return (
    <figure className={styles.cover}>
      {hero && delivery && failed !== hero.id ? (
        <>
          {/* biome-ignore lint/performance/noImgElement: only rights-approved stored media, with no third-party optimizer. */}
          <img
            src={delivery}
            alt={hero.title}
            lang={hero.source.language}
            decoding="async"
            onError={() => setFailed(hero.id)}
          />
          <figcaption className={styles.credit}>
            <bdi>{hero.author}</bdi>{" "}
            {licence && (
              <a href={licence} target="_blank" rel="noopener noreferrer">
                {hero.licence_code}
              </a>
            )}
          </figcaption>
        </>
      ) : (
        <>
          <span className={styles.coverMonogram} aria-hidden="true">
            {project.name
              .split(/\s+/)
              .slice(0, 2)
              .map((word) => word[0])
              .join("")}
          </span>
          <figcaption className={styles.coverCopy}>
            <span>{labels.visuals}</span>
            <bdi lang={project.language}>{project.name}</bdi>
            {website && (
              <a href={website} target="_blank" rel="noopener noreferrer">
                {labels.officialGallery} <span aria-hidden="true">↗</span>
              </a>
            )}
          </figcaption>
        </>
      )}
    </figure>
  );
}
