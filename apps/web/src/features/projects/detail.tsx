import navigation from "@property-platform/contracts/territories";
import type { ReactNode } from "react";
import { Link } from "@/i18n/navigation";
import { type ActivityLabels, describedParcels } from "./activity";
import { CancellationRetentionCard } from "./cancellation-retention";
import { ProjectActivitySection } from "./construction-activity";
import { ProjectCover } from "./cover";
import {
  type DeliveryLabels,
  developerHistoryHref,
  isDeveloperKey,
} from "./delivery";
import { ProjectDocuments } from "./documents";
import dossier from "./dossier.module.css";
import { Proof, ProofGroup, SourceLink, SourceRights } from "./evidence";
import { MediaCard } from "./media-card";
import { type ObservedSalesLabels, observedSalesCount } from "./observed-sales";
import { ProjectObservedSalesSection } from "./observed-sales-section";
import {
  formatHandover,
  formatProjectDate,
  groupProjectTypologies,
  projectAmenityKey,
  projectMedia,
  projectPositionQuality,
  projectRelations,
  projectWebsite,
} from "./presentation";
import styles from "./project.module.css";
import { ProjectComponents, ProjectParent } from "./relations";
import type { RetentionLabels } from "./retention";
import type { ProjectDetail, ProjectLabels } from "./types";
import type { VerificationLabels } from "./verification";
import { ProjectVerificationSection } from "./verification-sheet";

const typeKeys = new Set([
  "apartment",
  "duplex",
  "penthouse",
  "townhouse",
  "villa",
  "studio",
]);

export function ProjectDetailView({
  project,
  locale,
  labels,
  retentionLabels,
  verificationLabels,
  activityLabels,
  observedSalesLabels,
  deliveryLabels,
  neighbourhood,
}: {
  project: ProjectDetail;
  locale: string;
  labels: ProjectLabels;
  retentionLabels: RetentionLabels;
  verificationLabels: VerificationLabels;
  activityLabels: ActivityLabels;
  observedSalesLabels: ObservedSalesLabels;
  deliveryLabels: DeliveryLabels;
  neighbourhood?: ReactNode;
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
  const websiteInfo = projectWebsite(project);
  const website = websiteInfo.url;
  const websiteLabel = websiteInfo.official
    ? labels.developerWebsite
    : labels.source;
  const programmeLabel =
    project.programme_total?.basis === "registered"
      ? labels.registeredHomes
      : labels.plannedHomes;
  const { documents, visuals } = projectMedia(project);
  const quality = projectPositionQuality(project.map_locations);
  const typologies = groupProjectTypologies(project.typologies);
  const homeTypes = typologies.map((item) => item.property_type);
  const number = new Intl.NumberFormat(locale);
  const date = (value: string) =>
    formatProjectDate(value, locale) ?? labels.notDocumented;
  const areaLink = {
    pathname: "/explore",
    query: { territory: project.territory, project: project.slug },
  };
  const sections = [
    ["project-overview", labels.overview],
    ...(project.verification
      ? [["project-verification", verificationLabels.title]]
      : []),
    ...(project.construction_activity &&
    describedParcels(project.construction_activity).length
      ? [["project-activity", activityLabels.short]]
      : []),
    ...(projectRelations(project).components.length
      ? [["project-components", labels.components]]
      : []),
    ...(project.typologies.length ? [["project-homes", labels.homes]] : []),
    ...(project.observed_sales && observedSalesCount(project.observed_sales)
      ? [["project-sales", observedSalesLabels.short]]
      : []),
    ["project-documents", labels.documents],
    ...(project.amenities.length
      ? [["project-amenities", labels.amenities]]
      : []),
    ...(visuals.length ? [["project-media", labels.media]] : []),
    ["project-location", labels.location],
    ["project-purchase", labels.commercial],
  ];
  const sectionNavigation = (
    <nav className={styles.sectionNav} aria-label={labels.navigation}>
      {sections.map(([id, label]) => (
        <a key={id} href={`#${id}`}>
          {label}
        </a>
      ))}
    </nav>
  );
  return (
    <main
      className={styles.page}
      data-page="project"
      data-project-dossier={project.slug}
    >
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

      <header className={dossier.hero}>
        <div className={dossier.heroCopy}>
          <p className={styles.kicker}>
            {labels.project} <span aria-hidden="true"> / </span>{" "}
            <bdi>{territoryName}</bdi>
          </p>
          <h1 lang={project.language}>
            <bdi>{project.name}</bdi>
          </h1>
          <div className={styles.developer}>
            <span>{labels.developer}</span>
            <bdi>{project.developer.name}</bdi>
            {isDeveloperKey(project.developer.key) && (
              <Link
                className={dossier.developerHistory}
                href={developerHistoryHref(project.developer.key)}
              >
                {labels.deliveryHistory} <span aria-hidden="true">↗</span>
              </Link>
            )}
          </div>
          <ProjectParent project={project} labels={labels} locale={locale} />
          <dl className={dossier.facts}>
            <div>
              <dt>{labels.location}</dt>
              <dd>
                <bdi>{territoryName}</bdi>
              </dd>
            </div>
            <div>
              <dt>{labels.handover}</dt>
              <dd>{handover ?? labels.notDocumented}</dd>
            </div>
            {project.programme_total && (
              <div>
                <dt>{programmeLabel}</dt>
                <dd>{number.format(project.programme_total.value)}</dd>
              </div>
            )}
            {homeTypes.length > 0 && (
              <div>
                <dt>{labels.homes}</dt>
                <dd>
                  {homeTypes
                    .map((type) =>
                      typeKeys.has(type) ? labels[type as "apartment"] : type,
                    )
                    .join(" · ")}
                </dd>
              </div>
            )}
          </dl>
          {!project.map_locations.length && (
            <p className={dossier.locationNotice}>{labels.notMapped}</p>
          )}
          {quality && (
            <p className={dossier.locationNotice}>{labels[quality.label]}</p>
          )}
          <div className={styles.actions}>
            <a className={styles.primaryAction} href="#project-documents">
              {labels.documents} <span aria-hidden="true">↓</span>
            </a>
            <Link className={styles.secondaryAction} href={areaLink}>
              {labels.exploreArea} <span aria-hidden="true">↗</span>
            </Link>
          </div>
        </div>
        <ProjectCover key={project.id} project={project} labels={labels} />
      </header>
      {sectionNavigation}
      <div className={styles.contentLayout}>
        <div className={styles.mainColumn}>
          <section
            className={styles.section}
            aria-labelledby="project-overview"
          >
            <div className={styles.sectionHeading}>
              <h2 id="project-overview">{labels.overview}</h2>
            </div>
            {project.summary && (
              <p
                className={styles.description}
                lang={project.summary_source?.language ?? project.language}
                dir="auto"
              >
                {project.summary}
              </p>
            )}
            {!project.summary && !handover && !project.programme_total && (
              <p className={styles.muted}>{labels.notDocumented}</p>
            )}
            {project.summary_source && (
              <SourceLink source={project.summary_source} labels={labels} />
            )}
            <div className={styles.overviewFacts}>
              {handover && project.handover && (
                <article className={styles.highlight}>
                  <h3>{labels.handover}</h3>
                  <p className={styles.highlightValue}>{handover}</p>
                  <Proof
                    source={project.handover.source}
                    labels={labels}
                    locale={locale}
                  />
                </article>
              )}
              {project.programme_total && (
                <article className={styles.highlight}>
                  <h3>{programmeLabel}</h3>
                  <p className={styles.highlightValue}>
                    {number.format(project.programme_total.value)}
                  </p>
                  <p className={styles.muted}>{labels.programmeNote}</p>
                  <Proof
                    source={project.programme_total.source}
                    labels={labels}
                    locale={locale}
                  />
                </article>
              )}
            </div>
          </section>
          {project.verification && (
            <ProjectVerificationSection
              project={project}
              verification={project.verification}
              locale={locale}
              labels={verificationLabels}
              deliveryLabels={deliveryLabels}
              projectLabels={labels}
            />
          )}
          {project.construction_activity && (
            <ProjectActivitySection
              activity={project.construction_activity}
              locale={locale}
              labels={activityLabels}
              projectLabels={labels}
            />
          )}
          <ProjectComponents
            project={project}
            labels={labels}
            locale={locale}
          />
          {project.typologies.length > 0 && (
            <section className={styles.section} aria-labelledby="project-homes">
              <div className={styles.sectionHeading}>
                <h2 id="project-homes">{labels.homes}</h2>
              </div>
              <div className={dossier.typologies}>
                {typologies.map((item) => (
                  <article
                    className={dossier.typology}
                    key={item.property_type}
                  >
                    <h3>
                      {typeKeys.has(item.property_type) ? (
                        labels[item.property_type as "apartment"]
                      ) : (
                        <bdi>{item.property_type}</bdi>
                      )}
                    </h3>
                    <dl className={dossier.bedrooms}>
                      <dt>{labels.bedrooms}</dt>
                      <dd>
                        {item.bedrooms.length ? (
                          <ul className={dossier.variants}>
                            {item.bedrooms.map((bedrooms) => (
                              <li key={bedrooms}>
                                {bedrooms === 0
                                  ? labels.studio
                                  : number.format(bedrooms)}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          labels.bedroomsUnspecified
                        )}
                      </dd>
                    </dl>
                    <ProofGroup
                      sources={item.claims.map((claim) => claim.source)}
                      labels={labels}
                      locale={locale}
                    />
                  </article>
                ))}
              </div>
            </section>
          )}
          {project.observed_sales && (
            <ProjectObservedSalesSection
              sales={project.observed_sales}
              locale={locale}
              labels={observedSalesLabels}
              projectLabels={labels}
            />
          )}
          <ProjectDocuments
            documents={documents}
            labels={labels}
            locale={locale}
          />
          {project.amenities.length > 0 && (
            <section
              className={styles.section}
              aria-labelledby="project-amenities"
            >
              <div className={styles.sectionHeading}>
                <h2 id="project-amenities">{labels.amenities}</h2>
              </div>
              <div className={styles.amenities}>
                {project.amenities.map((item) => {
                  const key = projectAmenityKey(item.code);
                  return (
                    <article className={styles.amenity} key={item.code}>
                      <span className={styles.amenityDot} aria-hidden="true">
                        ◇
                      </span>
                      <div>
                        <h3
                          lang={key ? locale : item.source.language}
                          dir="auto"
                        >
                          {key ? labels[key] : item.label}
                        </h3>
                        <Proof
                          source={item.source}
                          labels={labels}
                          locale={locale}
                        />
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          )}
          {visuals.length > 0 && (
            <section className={styles.section} aria-labelledby="project-media">
              <div className={styles.sectionHeading}>
                <h2 id="project-media">{labels.media}</h2>
              </div>
              <div className={styles.media}>
                {visuals.map((item) => (
                  <MediaCard
                    media={item}
                    labels={labels}
                    key={item.id}
                    locale={locale}
                  />
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
            <Link className={styles.primaryAction} href={areaLink}>
              {labels.exploreArea} <span aria-hidden="true">↗</span>
            </Link>
          </section>
        </div>
        <section
          className={`${styles.section} ${dossier.purchase}`}
          aria-labelledby="project-purchase"
        >
          <div className={styles.sectionHeading}>
            <h2 id="project-purchase">{labels.commercial}</h2>
          </div>
          <div className={styles.commercial}>
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
            {project.cancellation_retention && (
              <CancellationRetentionCard
                retention={project.cancellation_retention}
                labels={retentionLabels}
                projectLabels={labels}
                locale={locale}
              />
            )}
            {website && (
              <a
                className={styles.textAction}
                href={website}
                target="_blank"
                rel="noopener noreferrer"
              >
                {websiteLabel} <span aria-hidden="true">↗</span>
              </a>
            )}
          </div>
        </section>
      </div>
      {project.sources.length > 0 && (
        <details className={styles.sources}>
          <summary>
            {labels.sources} <span aria-hidden="true">+</span>
          </summary>
          <p className={styles.muted}>{labels.sourceNote}</p>
          <p>
            <Link href="/sources">{labels.sourcesAndLicences}</Link>
          </p>
          {project.sources.map((source) => (
            <article
              className={styles.source}
              key={`${source.url}-${source.retrieved_at}-${source.content_sha256 ?? ""}`}
            >
              <SourceLink source={source} labels={labels} showDeveloper />
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
              <SourceRights source={source} labels={labels} />
            </article>
          ))}
        </details>
      )}
    </main>
  );
}
