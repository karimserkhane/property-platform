import navigation from "@property-platform/contracts/territories";
import { Link } from "@/i18n/navigation";
import {
  approvedDelivery,
  formatHandover,
  playableMedia,
  safeSourceUrl,
} from "./presentation";
import styles from "./project.module.css";
import type {
  ProjectDetail,
  ProjectLabels,
  ProjectMedia,
  ProjectSource,
} from "./types";

function SourceLink({
  source,
  labels,
}: {
  source: ProjectSource;
  labels: ProjectLabels;
}) {
  const url = safeSourceUrl(source.url);
  return url ? (
    <a href={url} target="_blank" rel="noopener noreferrer">
      {labels.source} · <bdi>{source.name}</bdi>{" "}
      <span aria-hidden="true">↗</span>
    </a>
  ) : null;
}

function Proof({
  source,
  original,
  labels,
}: {
  source: ProjectSource;
  original?: string;
  labels: ProjectLabels;
}) {
  return (
    <details className={styles.proof}>
      <summary>{labels.evidence}</summary>
      {original && (
        <p lang={source.language} dir="auto">
          {original}
        </p>
      )}
      {source.evidence_pointer && (
        <p lang={source.language} dir="auto">
          {source.evidence_pointer}
        </p>
      )}
      <SourceLink source={source} labels={labels} />
    </details>
  );
}

const typeKeys = new Set([
  "apartment",
  "duplex",
  "penthouse",
  "townhouse",
  "villa",
  "studio",
]);

function MediaCard({
  media,
  labels,
}: {
  media: ProjectMedia;
  labels: ProjectLabels;
}) {
  const delivery = approvedDelivery(media);
  const source = safeSourceUrl(media.source_url);
  const playable = playableMedia(media);
  const licence = safeSourceUrl(media.licence_url);
  const kind = ["image", "document", "video", "model"].includes(media.kind)
    ? (media.kind as "image" | "document" | "video" | "model")
    : "document";
  return (
    <article className={styles.mediaCard}>
      {playable === "image" && delivery && (
        // biome-ignore lint/performance/noImgElement: the API supplies only approved, typed stored media; this preserves controlled delivery without a remote optimizer.
        <img
          src={delivery}
          alt={media.title}
          lang={media.source.language}
          loading="lazy"
          decoding="async"
        />
      )}
      {playable === "video" && delivery && (
        // biome-ignore lint/a11y/useMediaCaption: Captions are not supplied by the reviewed source; the original media link remains available and no transcript is invented.
        <video controls preload="none" playsInline aria-label={media.title}>
          <source src={delivery} type={media.mime_type} />
          <a href={delivery} target="_blank" rel="noopener noreferrer">
            {labels.openFile}
          </a>
        </video>
      )}
      <div className={styles.mediaCopy}>
        <span className={styles.kicker}>{labels[kind]}</span>
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
      </div>
    </article>
  );
}

export function ProjectDetailView({
  project,
  locale,
  labels,
}: {
  project: ProjectDetail;
  locale: string;
  labels: ProjectLabels;
}) {
  const territory = navigation.territories.find(
    (item) => item.id === project.territory,
  );
  const territoryName = territory
    ? locale === "ar"
      ? territory.name_ar
      : territory.name
    : project.territory;
  const handover = project.handover
    ? formatHandover(project.handover, locale, labels.quarter)
    : null;
  const website = safeSourceUrl(project.website_url);
  const media = project.media.filter(
    (item) => item.rights_status !== "blocked",
  );
  const number = new Intl.NumberFormat(locale);
  const date = (value: string) =>
    new Intl.DateTimeFormat(locale, {
      dateStyle: "medium",
      timeZone: "Asia/Dubai",
    }).format(new Date(value));
  return (
    <main className={styles.page} data-page="project">
      <nav className={styles.breadcrumb} aria-label={labels.navigation}>
        <Link
          href={{
            pathname: "/explore",
            query: { territory: project.territory },
          }}
        >
          {labels.backToMap}
        </Link>
        <span aria-hidden="true">/</span>
        <bdi>{territoryName}</bdi>
      </nav>
      <header className={styles.hero}>
        <div className={styles.heroCopy}>
          <p className={styles.kicker}>
            {labels.project} · <bdi>{territoryName}</bdi>
          </p>
          <h1 lang={project.language} dir="auto">
            <bdi>{project.name}</bdi>
          </h1>
          <p className={styles.developer}>
            <span>{labels.developer}</span>
            <bdi>{project.developer.name}</bdi>
          </p>
          {project.summary && (
            <p
              className={styles.description}
              lang={project.language}
              dir="auto"
            >
              {project.summary}
            </p>
          )}
          <div className={styles.actions}>
            <Link
              className={styles.primaryAction}
              href={{
                pathname: "/explore",
                query: { territory: project.territory },
              }}
            >
              {labels.exploreArea} <span aria-hidden="true">↗</span>
            </Link>
            {website && (
              <a
                className={styles.secondaryAction}
                href={website}
                target="_blank"
                rel="noopener noreferrer"
              >
                {labels.developerWebsite} <span aria-hidden="true">↗</span>
              </a>
            )}
          </div>
        </div>
        {(handover || project.programme_total) && (
          <div className={styles.highlights}>
            {handover && project.handover && (
              <article className={styles.highlight}>
                <h2>{labels.handover}</h2>
                <p className={styles.highlightValue}>{handover}</p>
                <Proof
                  source={project.handover.source}
                  original={project.handover.original_text}
                  labels={labels}
                />
              </article>
            )}
            {project.programme_total && (
              <article className={styles.highlight}>
                <h2>{labels.plannedHomes}</h2>
                <p className={styles.highlightValue}>
                  {number.format(project.programme_total.value)}
                </p>
                <p className={styles.muted}>{labels.programmeNote}</p>
                <Proof
                  source={project.programme_total.source}
                  original={project.programme_total.original_text}
                  labels={labels}
                />
              </article>
            )}
          </div>
        )}
      </header>
      {project.typologies.length > 0 && (
        <section className={styles.section} aria-labelledby="project-homes">
          <div className={styles.sectionHeading}>
            <span aria-hidden="true">01 /</span>
            <h2 id="project-homes">{labels.homes}</h2>
          </div>
          <div className={styles.typologies}>
            {project.typologies.map((item) => (
              <article
                className={styles.typology}
                key={`${item.property_type}:${item.bedrooms}:${item.original_text}`}
              >
                <h3>
                  {typeKeys.has(item.property_type) ? (
                    labels[item.property_type as "apartment"]
                  ) : (
                    <bdi>{item.property_type}</bdi>
                  )}
                </h3>
                {item.bedrooms != null && (
                  <p>
                    {item.bedrooms === 0 ? (
                      labels.studio
                    ) : (
                      <>
                        {labels.bedrooms} : {number.format(item.bedrooms)}
                      </>
                    )}
                  </p>
                )}
                <Proof
                  source={item.source}
                  original={item.original_text}
                  labels={labels}
                />
              </article>
            ))}
          </div>
        </section>
      )}
      {project.amenities.length > 0 && (
        <section className={styles.section} aria-labelledby="project-amenities">
          <div className={styles.sectionHeading}>
            <span aria-hidden="true">02 /</span>
            <h2 id="project-amenities">{labels.amenities}</h2>
          </div>
          <div className={styles.amenities}>
            {project.amenities.map((item) => (
              <article className={styles.amenity} key={item.code}>
                <h3 lang={item.source.language} dir="auto">
                  {item.label}
                </h3>
                <Proof
                  source={item.source}
                  original={item.original_text}
                  labels={labels}
                />
              </article>
            ))}
          </div>
        </section>
      )}
      {media.length > 0 && (
        <section className={styles.section} aria-labelledby="project-media">
          <div className={styles.sectionHeading}>
            <span aria-hidden="true">03 /</span>
            <h2 id="project-media">{labels.media}</h2>
          </div>
          <div className={styles.media}>
            {media.map((item) => (
              <MediaCard media={item} labels={labels} key={item.id} />
            ))}
          </div>
        </section>
      )}
      {project.sources.length > 0 && (
        <section
          className={`${styles.section} ${styles.sources}`}
          aria-labelledby="project-sources"
        >
          <div className={styles.sectionHeading}>
            <span aria-hidden="true">04 /</span>
            <h2 id="project-sources">{labels.sources}</h2>
          </div>
          <p className={styles.muted}>{labels.sourceNote}</p>
          {project.sources.map((source) => (
            <article className={styles.source} key={source.url}>
              <SourceLink source={source} labels={labels} />
              <p>
                {labels.retrieved}{" "}
                <time dateTime={source.retrieved_at}>
                  {date(source.retrieved_at)}
                </time>
                {source.published_at && (
                  <>
                    {" "}
                    · {labels.published}{" "}
                    <time dateTime={source.published_at}>
                      {date(source.published_at)}
                    </time>
                  </>
                )}
              </p>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
