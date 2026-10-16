import navigation from "@property-platform/contracts/territories";
import type { ReactNode } from "react";
import { Link } from "@/i18n/navigation";
import { ProjectCover } from "./cover";
import {
  approvedDelivery,
  formatHandover,
  playableMedia,
  projectMedia,
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
  variant = "page",
  onSectionChange,
  onLocate,
  locateLabel,
  neighbourhood,
}: {
  project: ProjectDetail;
  locale: string;
  labels: ProjectLabels;
  variant?: "page" | "map";
  onSectionChange?: (id: string) => void;
  onLocate?: () => void;
  locateLabel?: string;
  neighbourhood?: ReactNode;
}) {
  const embedded = variant === "map";
  const Root = embedded ? "article" : "main";
  const Title = embedded ? "h2" : "h1";
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
  const { documents, visuals } = projectMedia(project);
  const homeTypes = [
    ...new Set(project.typologies.map((item) => item.property_type)),
  ];
  const number = new Intl.NumberFormat(locale);
  const date = (value: string) =>
    new Intl.DateTimeFormat(locale, {
      dateStyle: "medium",
      timeZone: "Asia/Dubai",
    }).format(new Date(value));
  const areaLink = {
    pathname: "/explore",
    query: { territory: project.territory, project: project.slug },
  };
  const sections = [
    ["project-overview", labels.overview],
    ...(project.typologies.length ? [["project-homes", labels.homes]] : []),
    ...(project.amenities.length
      ? [["project-amenities", labels.amenities]]
      : []),
    ...(visuals.length ? [["project-media", labels.media]] : []),
    ...(documents.length ? [["project-documents", labels.documents]] : []),
    ["project-location", labels.location],
  ];
  const sectionNavigation = (
    <nav className={styles.sectionNav} aria-label={labels.navigation}>
      {sections.map(([id, label]) =>
        embedded ? (
          <button type="button" key={id} onClick={() => onSectionChange?.(id)}>
            {label}
          </button>
        ) : (
          <a key={id} href={`#${id}`}>
            {label}
          </a>
        ),
      )}
    </nav>
  );
  return (
    <Root
      className={`${styles.page} ${embedded ? styles.embedded : ""}`}
      data-page="project"
      data-project-dossier={project.slug}
    >
      {!embedded && (
        <nav className={styles.breadcrumb} aria-label={labels.navigation}>
          <Link href={areaLink}>
            <span aria-hidden="true">←</span> {labels.backToMap}
          </Link>
          <span aria-hidden="true">/</span>
          <Link
            href={{
              pathname: "/projects",
              query: { territory: project.territory },
            }}
          >
            {labels.projects}
          </Link>
        </nav>
      )}
      <header className={styles.hero}>
        <div className={styles.heroCopy}>
          <p className={styles.kicker}>
            {labels.project} <span aria-hidden="true"> / </span>{" "}
            <bdi>{territoryName}</bdi>
          </p>
          <Title lang={project.language}>
            <bdi>{project.name}</bdi>
          </Title>
          <div className={styles.developer}>
            <span>{labels.developer}</span>
            <bdi>{project.developer.name}</bdi>
          </div>
          <div className={styles.actions}>
            {website && (
              <a
                className={styles.primaryAction}
                href={website}
                target="_blank"
                rel="noopener noreferrer"
              >
                {labels.developerWebsite} <span aria-hidden="true">↗</span>
              </a>
            )}
            {embedded ? (
              <Link
                className={styles.secondaryAction}
                href={`/projects/${project.slug}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {labels.openPage} <span aria-hidden="true">↗</span>
              </Link>
            ) : (
              <Link className={styles.secondaryAction} href={areaLink}>
                {labels.exploreArea} <span aria-hidden="true">↗</span>
              </Link>
            )}
          </div>
        </div>
        <ProjectCover key={project.id} project={project} labels={labels} />
      </header>
      <div className={styles.factStrip}>
        {handover && (
          <div>
            <span>{labels.handover}</span>
            <strong>{handover}</strong>
          </div>
        )}
        {project.programme_total && (
          <div>
            <span>{labels.plannedHomes}</span>
            <strong>{number.format(project.programme_total.value)}</strong>
          </div>
        )}
        {homeTypes.length > 0 && (
          <div>
            <span>{labels.homes}</span>
            <strong>
              {homeTypes
                .map((type) =>
                  typeKeys.has(type) ? labels[type as "apartment"] : type,
                )
                .join(" · ")}
            </strong>
          </div>
        )}
        <div>
          <span>{labels.location}</span>
          <strong>
            <bdi>{territoryName}</bdi>
          </strong>
        </div>
      </div>
      {sectionNavigation}
      <div className={styles.contentLayout}>
        <div className={styles.mainColumn}>
          <section
            className={styles.section}
            aria-labelledby="project-overview"
          >
            <div className={styles.sectionHeading}>
              <span aria-hidden="true">01 /</span>
              <h2 id="project-overview">{labels.overview}</h2>
            </div>
            {project.summary && (
              <p
                className={styles.description}
                lang={project.language}
                dir="auto"
              >
                {project.summary}
              </p>
            )}
            <div className={styles.overviewFacts}>
              {handover && project.handover && (
                <article className={styles.highlight}>
                  <h3>{labels.handover}</h3>
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
                  <h3>{labels.plannedHomes}</h3>
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
          </section>
          {project.typologies.length > 0 && (
            <section className={styles.section} aria-labelledby="project-homes">
              <div className={styles.sectionHeading}>
                <span aria-hidden="true">02 /</span>
                <h2 id="project-homes">{labels.homes}</h2>
              </div>
              <div className={styles.typologies}>
                {project.typologies.map((item) => (
                  <article
                    className={styles.typology}
                    key={`${item.property_type}:${item.bedrooms}:${item.original_text}`}
                  >
                    <span className={styles.homeNumber} aria-hidden="true">
                      {item.bedrooms == null
                        ? "—"
                        : item.bedrooms === 0
                          ? "S"
                          : number.format(item.bedrooms)}
                    </span>
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
            <section
              className={styles.section}
              aria-labelledby="project-amenities"
            >
              <div className={styles.sectionHeading}>
                <span aria-hidden="true">03 /</span>
                <h2 id="project-amenities">{labels.amenities}</h2>
              </div>
              <div className={styles.amenities}>
                {project.amenities.map((item) => (
                  <article className={styles.amenity} key={item.code}>
                    <span className={styles.amenityDot} aria-hidden="true">
                      ◇
                    </span>
                    <div>
                      <h3 lang={item.source.language} dir="auto">
                        {item.label}
                      </h3>
                      <Proof
                        source={item.source}
                        original={item.original_text}
                        labels={labels}
                      />
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}
          {visuals.length > 0 && (
            <section className={styles.section} aria-labelledby="project-media">
              <div className={styles.sectionHeading}>
                <span aria-hidden="true">04 /</span>
                <h2 id="project-media">{labels.media}</h2>
              </div>
              <div className={styles.media}>
                {visuals.map((item) => (
                  <MediaCard media={item} labels={labels} key={item.id} />
                ))}
              </div>
            </section>
          )}
          <section
            className={`${styles.section} ${styles.location}`}
            aria-labelledby="project-location"
          >
            <p className={styles.kicker}>{labels.location}</p>
            <h2 id="project-location">
              <bdi>{territoryName}</bdi>
            </h2>
            {neighbourhood}
            {embedded ? (
              onLocate ? (
                <button
                  type="button"
                  className={styles.primaryAction}
                  onClick={onLocate}
                >
                  {locateLabel ?? labels.exploreArea}
                </button>
              ) : (
                <p className={styles.muted}>{labels.notMapped}</p>
              )
            ) : (
              <Link className={styles.primaryAction} href={areaLink}>
                {labels.exploreArea} <span aria-hidden="true">↗</span>
              </Link>
            )}
          </section>
        </div>
        <aside className={styles.sidebar} aria-label={labels.commercial}>
          {documents.length > 0 && (
            <section
              className={styles.documentSection}
              aria-labelledby="project-documents"
            >
              <div className={styles.sectionHeading}>
                <h2 id="project-documents">{labels.documents}</h2>
                <span>{number.format(documents.length)}</span>
              </div>
              <div className={styles.documents}>
                {documents.map((item) => (
                  <MediaCard media={item} labels={labels} key={item.id} />
                ))}
              </div>
            </section>
          )}
          <details className={styles.commercial}>
            <summary>
              {labels.commercial}
              <span aria-hidden="true">+</span>
            </summary>
            <p className={styles.purchaseNote}>{labels.purchaseNote}</p>
            <dl>
              {[
                labels.price,
                labels.paymentPlan,
                labels.serviceCharge,
                labels.availability,
              ].map((label) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{labels.notDocumented}</dd>
                </div>
              ))}
            </dl>
            {website && (
              <a
                className={styles.textAction}
                href={website}
                target="_blank"
                rel="noopener noreferrer"
              >
                {labels.developerWebsite} <span aria-hidden="true">↗</span>
              </a>
            )}
          </details>
        </aside>
      </div>
      {project.sources.length > 0 && (
        <details className={styles.sources}>
          <summary>
            {labels.sources} <span aria-hidden="true">+</span>
          </summary>
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
        </details>
      )}
    </Root>
  );
}
