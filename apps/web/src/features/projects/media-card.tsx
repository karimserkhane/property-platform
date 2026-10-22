import { Proof } from "./evidence";
import {
  approvedDelivery,
  mediaLabel,
  playableMedia,
  safeSourceUrl,
} from "./presentation";
import styles from "./project.module.css";
import type { ProjectLabels, ProjectMedia } from "./types";

export function MediaCard({
  media,
  labels,
  locale,
}: {
  media: ProjectMedia;
  labels: ProjectLabels;
  locale: string;
}) {
  const delivery = approvedDelivery(media);
  const source = safeSourceUrl(media.source_url);
  const playable = playableMedia(media);
  const licence = safeSourceUrl(media.licence_url);
  return (
    <article className={styles.mediaCard}>
      {playable === "image" && delivery && (
        // biome-ignore lint/performance/noImgElement: approved typed storage is delivered without a remote optimizer.
        <img
          src={delivery}
          alt={media.title}
          lang={media.source.language}
          loading="lazy"
          decoding="async"
        />
      )}
      {playable === "video" && delivery && (
        // biome-ignore lint/a11y/useMediaCaption: the source supplies no captions; the original link remains available.
        <video controls preload="none" playsInline aria-label={media.title}>
          <source src={delivery} type={media.mime_type} />
          <a href={delivery} target="_blank" rel="noopener noreferrer">
            {labels.openFile}
          </a>
        </video>
      )}
      <div className={styles.mediaCopy}>
        <span className={styles.kicker}>{labels[mediaLabel(media)]}</span>
        <h3 lang={media.source.language} dir="auto">
          {media.title}
        </h3>
        {delivery && !playable && (
          <a
            className={styles.textAction}
            href={delivery}
            target="_blank"
            rel="noopener noreferrer"
          >
            {labels.openFile} <span aria-hidden="true">↗</span>
          </a>
        )}
        {source && (
          <a
            className={styles.textAction}
            href={source}
            target="_blank"
            rel="noopener noreferrer"
          >
            {labels.viewSource} <span aria-hidden="true">↗</span>
          </a>
        )}
        {!delivery && <p className={styles.muted}>{labels.referenceOnly}</p>}
        {(media.author || media.licence_code) && (
          <p className={styles.muted}>
            {media.author && <bdi>{media.author}</bdi>}
            {media.author && media.licence_code && " · "}
            {licence ? (
              <a href={licence} target="_blank" rel="noopener noreferrer">
                {media.licence_code}
              </a>
            ) : (
              media.licence_code
            )}
          </p>
        )}
        <Proof source={media.source} labels={labels} locale={locale} />
      </div>
    </article>
  );
}
