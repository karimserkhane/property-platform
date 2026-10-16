"use client";

import { useLocale } from "next-intl";
import { useState } from "react";
import {
  approvedDelivery,
  playableMedia,
  projectMedia,
  safeSourceUrl,
} from "./presentation";
import styles from "./project.module.css";
import type { ProjectDetail, ProjectLabels } from "./types";

// Existing licensed editorial assets stay distinct from project evidence.
const editorial = [
  { image: "abu-dhabi-sunset", position: "66% 58%" },
  { image: "abu-dhabi-coast", position: "50% 74%" },
] as const;

export function ProjectCover({
  project,
  labels,
  compact = false,
}: {
  project: ProjectDetail;
  compact?: boolean;
  labels: Pick<
    ProjectLabels,
    | "visuals"
    | "officialGallery"
    | "editorialImage"
    | "previousImage"
    | "nextImage"
  >;
}) {
  const locale = useLocale();
  const { hero, visuals } = projectMedia(project);
  const [index, setIndex] = useState(0);
  const [failed, setFailed] = useState<string[]>([]);
  const images = [
    ...(hero ? [hero] : []),
    ...visuals.filter(
      (item) => item.id !== hero?.id && playableMedia(item) === "image",
    ),
  ].filter((item) => !failed.includes(item.id));
  const photo = images[index % Math.max(images.length, 1)];
  const ambient = editorial[index % editorial.length];
  const delivery = photo && approvedDelivery(photo);
  const total = images.length || editorial.length;
  const website = safeSourceUrl(project.website_url);
  const licence = safeSourceUrl(photo?.licence_url);
  const move = (step: number) =>
    setIndex((value) => (value + step + total) % total);
  const number = new Intl.NumberFormat(locale);
  return (
    <figure
      className={`${styles.cover} ${compact ? styles.summaryCover : ""}`}
      data-editorial={!delivery}
    >
      {/* biome-ignore lint/performance/noImgElement: approved stored media or existing local licensed editorial assets; no remote optimizer. */}
      <img
        key={delivery || ambient.image}
        src={delivery || `/images/uae/${ambient.image}-1920.webp`}
        srcSet={
          delivery
            ? undefined
            : `/images/uae/${ambient.image}-768.webp 768w, /images/uae/${ambient.image}-1920.webp 1920w`
        }
        sizes={
          compact
            ? "(max-width: 760px) 100vw, 380px"
            : "(max-width: 760px) 100vw, 1400px"
        }
        alt={delivery ? photo.title : ""}
        lang={photo?.source.language}
        decoding="async"
        style={delivery ? undefined : { objectPosition: ambient.position }}
        onError={
          delivery
            ? () => setFailed((value) => [...value, photo.id])
            : undefined
        }
      />
      <figcaption className={styles.credit}>
        {delivery ? (
          <>
            <bdi>{photo.author}</bdi>
            {licence && (
              <a href={licence} target="_blank" rel="noopener noreferrer">
                {photo.licence_code}
              </a>
            )}
          </>
        ) : (
          <span>{labels.editorialImage}</span>
        )}
      </figcaption>
      {!compact && (
        <div className={styles.galleryControls}>
          {website && !delivery && (
            <a href={website} target="_blank" rel="noopener noreferrer">
              {labels.officialGallery} <span aria-hidden="true">↗</span>
            </a>
          )}
          {total > 1 && (
            <div className={styles.galleryPager}>
              <button
                type="button"
                aria-label={labels.previousImage}
                onClick={() => move(-1)}
              >
                ←
              </button>
              <output aria-label={labels.visuals} aria-live="polite">
                <bdi>
                  {number.format((index % total) + 1)} / {number.format(total)}
                </bdi>
              </output>
              <button
                type="button"
                aria-label={labels.nextImage}
                onClick={() => move(1)}
              >
                →
              </button>
            </div>
          )}
        </div>
      )}
    </figure>
  );
}
