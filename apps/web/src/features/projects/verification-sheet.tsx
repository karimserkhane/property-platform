import type { ReactNode } from "react";
import { Link } from "@/i18n/navigation";
import type { DeliveryLabels } from "./delivery";
import { developerHistoryHref, isDeveloperKey } from "./delivery";
import delivery from "./delivery.module.css";
import { Announcement, RegisterReadings } from "./delivery-history";
import dossier from "./dossier.module.css";
import { Proof } from "./evidence";
import { formatProjectDate, safeSourceUrl } from "./presentation";
import styles from "./project.module.css";
import { formatPercent } from "./retention";
import type { ProjectDetail, ProjectLabels } from "./types";
import {
  contradictionKey,
  contradictionKeysFor,
  hasVerification,
  knownContradictions,
  type ProjectVerification,
  type VerificationContradiction,
  type VerificationLabels,
} from "./verification";

type Shared = {
  locale: string;
  labels: VerificationLabels;
  deliveryLabels: DeliveryLabels;
  projectLabels: ProjectLabels;
};

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function Day({ value, locale }: { value: string; locale: string }) {
  return (
    <time dateTime={value}>{formatProjectDate(value, locale) ?? value}</time>
  );
}

function LatestReading({
  reading,
  locale,
  labels,
  projectLabels,
}: Shared & {
  reading: NonNullable<ProjectVerification["latest_reading"]>;
}) {
  const stated = (value: string | null) =>
    value ? <bdi>{value}</bdi> : labels.notStated;
  const report = reading.progress_report_url
    ? safeSourceUrl(reading.progress_report_url)
    : null;
  return (
    <article
      className={`${styles.highlight} ${dossier.verification}`}
      aria-labelledby="verification-latest"
      data-verification-reading
    >
      <h3 id="verification-latest">{labels.latestReading}</h3>
      <p className={styles.muted}>
        {labels.readOn} <Day value={reading.observed_at} locale={locale} />
      </p>
      <dl className={dossier.verificationFacts}>
        <Fact label={labels.registerStatus}>
          {reading.register_status ? (
            <bdi lang="en">{reading.register_status}</bdi>
          ) : (
            labels.notStated
          )}
        </Fact>
        <Fact label={labels.registrationNumber}>
          <bdi>{reading.registration_number}</bdi>
        </Fact>
        {reading.permit_number && (
          <Fact label={labels.permitNumber}>
            <bdi>{reading.permit_number}</bdi>
          </Fact>
        )}
        <Fact label={labels.offPlan}>
          {reading.off_plan === null
            ? labels.notStated
            : reading.off_plan
              ? labels.yes
              : labels.no}
        </Fact>
        {reading.registered_on && (
          <Fact label={labels.registeredOn}>
            <Day value={reading.registered_on} locale={locale} />
          </Fact>
        )}
        <Fact label={labels.progress}>
          {reading.progress_percent === null
            ? labels.notStated
            : formatPercent(reading.progress_percent, locale)}
          {reading.progress_inspected_on && (
            <>
              {" · "}
              {labels.inspectedOn}{" "}
              <Day value={reading.progress_inspected_on} locale={locale} />
            </>
          )}
        </Fact>
        {reading.inspection_company && (
          <Fact label={labels.inspectionCompany}>
            <bdi>{reading.inspection_company}</bdi>
          </Fact>
        )}
        {(report || reading.progress_report_valid_until) && (
          <Fact label={labels.progressReport}>
            {report && (
              <a href={report} target="_blank" rel="noopener noreferrer">
                {labels.progressReport} <span aria-hidden="true">↗</span>
              </a>
            )}
            {reading.progress_report_valid_until && (
              <>
                {report && " · "}
                {labels.validUntil}{" "}
                <Day
                  value={reading.progress_report_valid_until}
                  locale={locale}
                />
              </>
            )}
            {reading.progress_report_expired && (
              <strong
                className={dossier.verificationWarning}
                data-verification-report-expired
              >
                {" · "}
                {labels.reportExpired}
              </strong>
            )}
          </Fact>
        )}
        <Fact label={labels.sold}>
          {reading.sold_percent !== null
            ? formatPercent(reading.sold_percent, locale)
            : stated(reading.sold_original)}
        </Fact>
        <Fact label={labels.escrowBank}>
          {stated(reading.escrow_bank_name)}
        </Fact>
        {reading.escrow_account_number && (
          <Fact label={labels.escrowAccount}>
            <bdi dir="ltr">{reading.escrow_account_number}</bdi>
          </Fact>
        )}
        {reading.developer_licence && (
          <Fact label={labels.developerLicence}>
            <bdi>{reading.developer_licence}</bdi>
          </Fact>
        )}
      </dl>
      <Proof source={reading.source} labels={projectLabels} locale={locale} />
    </article>
  );
}

function Contradiction({
  item,
  locale,
  labels,
  deliveryLabels,
  projectLabels,
}: Shared & { item: VerificationContradiction }) {
  const keys = contradictionKeysFor(item.code);
  if (!keys) return null;
  const shared = { locale, labels: deliveryLabels, projectLabels };
  return (
    <li
      className={dossier.verificationCheck}
      data-verification-check={item.code}
    >
      <strong>{labels[keys.title]}</strong>
      <p className={styles.muted}>{labels[keys.note]}</p>
      {item.late_by_at_least_days != null && (
        <p className={delivery.outcome} data-delivery-outcome="late">
          {deliveryLabels.lateAtLeast}{" "}
          {new Intl.NumberFormat(locale).format(item.late_by_at_least_days)}{" "}
          {deliveryLabels.days}
        </p>
      )}
      {item.announcements.length > 0 && (
        <ul className={delivery.points}>
          {item.announcements.map((point) => (
            <Announcement
              key={`${point.source.url}:${point.first_observed_at}`}
              point={point}
              {...shared}
            />
          ))}
        </ul>
      )}
      {item.register_readings.length > 0 && (
        <RegisterReadings readings={item.register_readings} {...shared} />
      )}
    </li>
  );
}

/** What the register states, where cited sources disagree, and how to check it. */
export function ProjectVerificationSection({
  project,
  verification,
  ...shared
}: Shared & { project: ProjectDetail; verification: ProjectVerification }) {
  const { locale, labels, deliveryLabels, projectLabels } = shared;
  const known = hasVerification(verification);
  const checks = knownContradictions(verification);
  const links = verification.official_links.flatMap((link) => {
    const url = safeSourceUrl(link.url);
    return url ? [{ ...link, url }] : [];
  });
  return (
    <section
      className={styles.section}
      aria-labelledby="project-verification"
      data-project-verification={known ? "observed" : "none"}
    >
      <div className={styles.sectionHeading}>
        <h2 id="project-verification">{labels.title}</h2>
      </div>
      <p className={styles.muted}>{labels.intro}</p>
      {verification.latest_reading ? (
        <LatestReading reading={verification.latest_reading} {...shared} />
      ) : (
        <p>{labels.noReading}</p>
      )}
      {verification.completion && (
        <p className={delivery.completion}>
          {labels.completion}{" "}
          <Day value={verification.completion.observed_at} locale={locale} />
        </p>
      )}
      {known && (
        <>
          <h3 className={dossier.verificationHeading}>{labels.checks}</h3>
          {checks.length ? (
            <ul className={dossier.verificationChecks}>
              {checks.map((item) => (
                <Contradiction
                  key={contradictionKey(item)}
                  item={item}
                  {...shared}
                />
              ))}
            </ul>
          ) : (
            <p className={styles.muted}>{labels.noContradictions}</p>
          )}
          {checks.length > 0 && (
            <p className={styles.muted}>{labels.checksLimits}</p>
          )}
        </>
      )}
      {verification.register_readings.length > 0 && (
        <details className={`${styles.proof} ${dossier.proof}`}>
          <summary>{labels.history}</summary>
          <RegisterReadings
            readings={verification.register_readings}
            locale={locale}
            labels={deliveryLabels}
            projectLabels={projectLabels}
          />
        </details>
      )}
      <h3 className={dossier.verificationHeading}>{labels.officialLinks}</h3>
      {links.length ? (
        <ul className={dossier.verificationLinks}>
          {links.map((link) => (
            <li key={link.url}>
              <a href={link.url} target="_blank" rel="noopener noreferrer">
                {labels.officialLink} · <bdi>{link.registration_number}</bdi>{" "}
                <span aria-hidden="true">↗</span>
              </a>
              <p className={styles.muted}>
                {labels.reviewedOn}{" "}
                <Day value={link.reviewed_on} locale={locale} />
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.muted}>{labels.noOfficialLink}</p>
      )}
      <div className={dossier.verificationActions}>
        {isDeveloperKey(project.developer.key) && (
          <Link
            className={styles.textAction}
            href={developerHistoryHref(project.developer.key)}
          >
            {projectLabels.deliveryHistory} <span aria-hidden="true">↗</span>
          </Link>
        )}
        {project.cancellation_retention && (
          <a className={styles.textAction} href="#project-retention">
            {labels.retentionLink} <span aria-hidden="true">↓</span>
          </a>
        )}
      </div>
      <p className={styles.muted}>{labels.notAdvice}</p>
    </section>
  );
}
