import { Link } from "@/i18n/navigation";
import {
  formatProjectDate,
  sourceRightsNotice,
} from "../projects/presentation";
import project from "../projects/project.module.css";
import type { ProjectLabels } from "../projects/types";
import {
  familyLabelKey,
  freshnessLabelKey,
  freshnessState,
  type KnownFamily,
  publicationLabelKey,
  type SourceSite,
  type SourcesLabels,
  sortSourceSites,
} from "./data";
import styles from "./sources.module.css";

type LicenceLabels = Pick<
  ProjectLabels,
  | "projects"
  | "navigation"
  | "rightsUnreviewed"
  | "rightsReserved"
  | "rightsPerItem"
  | "rightsTerms"
>;

function Site({
  site,
  locale,
  labels,
  licenceLabels,
}: {
  site: SourceSite;
  locale: string;
  labels: SourcesLabels;
  licenceLabels: LicenceLabels;
}) {
  const notice = sourceRightsNotice(site);
  const licence = notice.labelKey ? (
    licenceLabels[notice.labelKey]
  ) : (
    <bdi dir="ltr">{notice.licence}</bdi>
  );
  const reviewed = site.reviewed_on
    ? formatProjectDate(site.reviewed_on, locale)
    : null;
  return (
    <article className={styles.site} data-source-site={site.host}>
      <h2>
        <bdi>{site.publisher}</bdi>
      </h2>
      <p className={styles.host}>
        <bdi dir="ltr">{site.host}</bdi>
      </p>
      <dl className={styles.facts}>
        <div>
          <dt>{labels.licence}</dt>
          <dd data-source-licence>
            {notice.licenceUrl ? (
              <a
                href={notice.licenceUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                {licence}
              </a>
            ) : (
              licence
            )}
          </dd>
        </div>
        <div>
          <dt>{labels.publication}</dt>
          <dd>{labels[publicationLabelKey(site.publication)]}</dd>
        </div>
        <div>
          <dt>{labels.collection}</dt>
          <dd>
            {site.collection === "allowed"
              ? labels.collectionAllowed
              : labels.collectionForbidden}
          </dd>
        </div>
        <div>
          <dt>{labels.reviewed}</dt>
          <dd>
            {site.reviewed_on && reviewed ? (
              <time dateTime={site.reviewed_on}>{reviewed}</time>
            ) : (
              labels.notReviewed
            )}
          </dd>
        </div>
      </dl>
      {notice.attribution && (
        <p className={styles.attribution}>
          {labels.attribution} <bdi>{notice.attribution}</bdi>
        </p>
      )}
      {notice.termsUrl && (
        <p>
          <a href={notice.termsUrl} target="_blank" rel="noopener noreferrer">
            {licenceLabels.rightsTerms} <span aria-hidden="true">↗</span>
          </a>
        </p>
      )}
    </article>
  );
}

function Dated({
  label,
  value,
  locale,
}: {
  label: string;
  value: string;
  locale: string;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>
        <time dateTime={value}>{formatProjectDate(value, locale)}</time>
      </dd>
    </div>
  );
}

function Freshness({
  families,
  now,
  locale,
  labels,
  behindSources,
}: {
  families: KnownFamily[];
  now: Date;
  locale: string;
  labels: SourcesLabels;
  behindSources: (behind: number, total: number) => string;
}) {
  return (
    <section className={styles.freshness} aria-labelledby="source-freshness">
      <h2 id="source-freshness">{labels.freshnessTitle}</h2>
      <p>{labels.freshnessIntro}</p>
      <ul>
        {families.map((row) => {
          const state = freshnessState(row, now);
          return (
            <li
              key={row.family}
              data-source-family={row.family}
              data-freshness={state}
            >
              <h3>{labels[familyLabelKey(row.family)]}</h3>
              <p className={styles.state}>{labels[freshnessLabelKey(state)]}</p>
              <dl className={styles.facts}>
                {row.last_success_at && (
                  <Dated
                    label={labels.freshnessLastSuccess}
                    value={row.last_success_at}
                    locale={locale}
                  />
                )}
                {row.late_from && state !== "current" && (
                  <Dated
                    label={labels.freshnessOverdueSince}
                    value={row.late_from}
                    locale={locale}
                  />
                )}
              </dl>
              {row.sources_behind > 0 && (
                <p className={styles.count}>
                  {behindSources(row.sources_behind, row.sources_total)}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function SourcesView({
  sites,
  count,
  locale,
  labels,
  licenceLabels,
  families,
  now,
  behindSources,
}: {
  sites: SourceSite[];
  count: string;
  locale: string;
  labels: SourcesLabels;
  licenceLabels: LicenceLabels;
  families: KnownFamily[] | null;
  now: Date;
  behindSources: (behind: number, total: number) => string;
}) {
  const sorted = sortSourceSites(sites, locale);
  return (
    <main className={project.page} data-page="source-rights">
      <nav className={project.breadcrumb} aria-label={licenceLabels.navigation}>
        <Link href="/projects">
          <span aria-hidden="true">←</span> {licenceLabels.projects}
        </Link>
      </nav>
      <header className={styles.header}>
        <h1>{labels.title}</h1>
        <p className={project.description}>{labels.intro}</p>
        <p className={styles.count}>{count}</p>
      </header>
      {families && (
        <Freshness
          families={families}
          now={now}
          locale={locale}
          labels={labels}
          behindSources={behindSources}
        />
      )}
      <div className={styles.sites}>
        {sorted.map((site) => (
          <Site
            key={site.host}
            site={site}
            locale={locale}
            labels={labels}
            licenceLabels={licenceLabels}
          />
        ))}
      </div>
    </main>
  );
}
