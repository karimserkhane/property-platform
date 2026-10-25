import { Link } from "@/i18n/navigation";
import {
  type DeliveryAnnouncement,
  type DeliveryHistory,
  type DeliveryLabels,
  type DeliveryProject,
  deliveryChangeKey,
  deliveryOutcomeKey,
  splitDeliveryProjects,
} from "./delivery";
import styles from "./delivery.module.css";
import dossier from "./dossier.module.css";
import { Proof } from "./evidence";
import { formatHandover, formatProjectDate } from "./presentation";
import project from "./project.module.css";
import type { ProjectLabels } from "./types";

export type Shared = {
  locale: string;
  labels: DeliveryLabels;
  projectLabels: ProjectLabels;
};

function Observed({
  first,
  last,
  readings,
  locale,
  labels,
}: {
  first: string;
  last: string;
  readings: number;
  locale: string;
  labels: DeliveryLabels;
}) {
  const from = formatProjectDate(first, locale);
  const to = formatProjectDate(last, locale);
  const number = new Intl.NumberFormat(locale);
  return (
    <p className={project.muted}>
      {labels.observed} <time dateTime={first}>{from}</time>
      {to && to !== from && (
        <>
          {" – "}
          <time dateTime={last}>{to}</time>
        </>
      )}{" "}
      · {labels.readings} {number.format(readings)}
    </p>
  );
}

export function Announcement({
  point,
  locale,
  labels,
  projectLabels,
}: Shared & { point: DeliveryAnnouncement }) {
  const value = formatHandover(point, locale, projectLabels.quarter);
  const change = deliveryChangeKey(point.change);
  const outcome = deliveryOutcomeKey(point.outcome.status);
  const days = point.outcome.late_by_at_least_days;
  return (
    <li className={styles.point} data-delivery-announcement={point.change}>
      <div className={styles.pointHeading}>
        <strong>{value ?? point.original_text}</strong>
        {change && <span className={styles.badge}>{labels[change]}</span>}
      </div>
      {value && (
        <p className={project.muted} dir="auto">
          {labels.originalText} · <bdi>{point.original_text}</bdi>
        </p>
      )}
      <Observed
        first={point.first_observed_at}
        last={point.last_observed_at}
        readings={point.readings}
        locale={locale}
        labels={labels}
      />
      {outcome && (
        <p
          className={styles.outcome}
          data-delivery-outcome={point.outcome.status}
        >
          {labels[outcome]}
          {days != null && (
            <>
              {" · "}
              {labels.lateAtLeast} {new Intl.NumberFormat(locale).format(days)}{" "}
              {labels.days}
            </>
          )}
        </p>
      )}
      <Proof source={point.source} labels={projectLabels} locale={locale} />
      {point.outcome.source && (
        <div className={styles.outcomeProof}>
          <span className={project.muted}>{labels.outcomeProof}</span>
          <Proof
            source={point.outcome.source}
            labels={projectLabels}
            locale={locale}
          />
        </div>
      )}
    </li>
  );
}

export function RegisterReadings({
  readings,
  locale,
  labels,
  projectLabels,
}: Shared & { readings: DeliveryProject["register_readings"] }) {
  if (!readings.length)
    return <p className={project.muted}>{labels.noRegister}</p>;
  const percent = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
  return (
    <ul className={styles.points}>
      {readings.map((reading) => (
        <li
          className={styles.point}
          key={`${reading.first_observed_at}:${reading.status}`}
          data-delivery-register={reading.completed ? "completed" : "open"}
        >
          <div className={styles.pointHeading}>
            <strong>
              {reading.completed ? labels.completed : labels.notCompleted}
            </strong>
            <span className={styles.badge}>
              {labels.registerStatus} · <bdi lang="en">{reading.status}</bdi>
            </span>
          </div>
          {reading.progress_percent != null && (
            <p className={project.muted}>
              {labels.progress} {percent.format(reading.progress_percent)} %
              {reading.progress_inspected_on && (
                <>
                  {" · "}
                  {labels.inspected}{" "}
                  <time dateTime={reading.progress_inspected_on}>
                    {formatProjectDate(reading.progress_inspected_on, locale)}
                  </time>
                </>
              )}
            </p>
          )}
          <Observed
            first={reading.first_observed_at}
            last={reading.last_observed_at}
            readings={reading.readings}
            locale={locale}
            labels={labels}
          />
          <Proof
            source={reading.source}
            labels={projectLabels}
            locale={locale}
          />
        </li>
      ))}
    </ul>
  );
}

function ProjectHistory({
  item,
  locale,
  labels,
  projectLabels,
}: Shared & { item: DeliveryProject }) {
  const id = `delivery-${item.slug}`;
  const shared = { locale, labels, projectLabels };
  const completed = item.completion
    ? formatProjectDate(item.completion.observed_at, locale)
    : null;
  const before = item.completion?.not_completed_until
    ? formatProjectDate(item.completion.not_completed_until, locale)
    : null;
  return (
    <section
      className={`${project.section} ${styles.project}`}
      aria-labelledby={id}
      data-delivery-project={item.slug}
    >
      <div className={project.sectionHeading}>
        <h2 id={id}>
          <Link className={styles.projectLink} href={`/projects/${item.slug}`}>
            <bdi>{item.name}</bdi>
          </Link>
        </h2>
      </div>
      {completed && (
        <p className={styles.completion}>
          {labels.completionObserved}{" "}
          <time dateTime={item.completion?.observed_at}>{completed}</time>
          {before && (
            <>
              {" · "}
              {labels.notCompletedUntil}{" "}
              <time dateTime={item.completion?.not_completed_until ?? ""}>
                {before}
              </time>
            </>
          )}
        </p>
      )}
      <div className={styles.columns}>
        <div>
          <h3>{labels.announcements}</h3>
          {item.announcements.length ? (
            <ul className={styles.points}>
              {item.announcements.map((point) => (
                <Announcement
                  key={`${point.source.url}:${point.first_observed_at}`}
                  point={point}
                  {...shared}
                />
              ))}
            </ul>
          ) : (
            <p className={project.muted}>{labels.noAnnouncements}</p>
          )}
        </div>
        <div>
          <h3>{labels.register}</h3>
          <RegisterReadings readings={item.register_readings} {...shared} />
        </div>
      </div>
    </section>
  );
}

export function DeliveryHistoryView({
  history,
  locale,
  labels,
  projectLabels,
}: Shared & { history: DeliveryHistory }) {
  const number = new Intl.NumberFormat(locale);
  const { observed, silent } = splitDeliveryProjects(history.projects);
  const summary = [
    [labels.projects, history.summary.projects],
    [labels.withAnnouncements, history.summary.with_announcements],
    [labels.withRegister, history.summary.with_register],
    [labels.completedObserved, history.summary.completed_observed],
    [labels.lateObserved, history.summary.late_observed],
    [labels.movedLater, history.summary.announcement_moved_later],
  ] as const;
  return (
    <main
      className={project.page}
      data-page="developer-delivery"
      data-developer={history.developer.key}
    >
      <nav className={project.breadcrumb} aria-label={projectLabels.navigation}>
        <Link href="/projects">
          <span aria-hidden="true">←</span> {projectLabels.projects}
        </Link>
      </nav>
      <header className={styles.header}>
        <p className={project.kicker}>
          {projectLabels.developer} <span aria-hidden="true"> / </span>{" "}
          {labels.title}
        </p>
        <h1>
          <bdi>{history.developer.name}</bdi>
        </h1>
        <p className={project.description}>{labels.intro}</p>
        <dl className={dossier.facts}>
          {summary.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{number.format(value)}</dd>
            </div>
          ))}
        </dl>
        <p className={project.muted}>{labels.limits}</p>
      </header>
      {observed.map((item) => (
        <ProjectHistory
          key={item.slug}
          item={item}
          locale={locale}
          labels={labels}
          projectLabels={projectLabels}
        />
      ))}
      {silent.length > 0 && (
        <section className={project.section} aria-labelledby="delivery-silent">
          <div className={project.sectionHeading}>
            <h2 id="delivery-silent">{labels.withoutObservations}</h2>
          </div>
          <ul className={styles.silent}>
            {silent.map((item) => (
              <li key={item.slug}>
                <Link href={`/projects/${item.slug}`}>
                  <bdi>{item.name}</bdi>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
