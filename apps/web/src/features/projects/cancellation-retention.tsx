import dossier from "./dossier.module.css";
import { Proof, SourceRights } from "./evidence";
import { formatProjectDate, safeSourceUrl } from "./presentation";
import styles from "./project.module.css";
import {
  type CancellationRetention,
  formatPercent,
  type RetentionLabels,
  retentionRates,
} from "./retention";
import type { ProjectLabels } from "./types";

/** Retention a developer may keep on cancellation, read at the latest declared stage. */
export function CancellationRetentionCard({
  retention,
  labels,
  projectLabels,
  locale,
}: {
  retention: CancellationRetention;
  labels: RetentionLabels;
  projectLabels: ProjectLabels;
  locale: string;
}) {
  const rates = retentionRates(retention, locale);
  const inspected = retention.progress_inspected_on
    ? formatProjectDate(retention.progress_inspected_on, locale)
    : null;
  const references = retention.source.references.flatMap((reference) => {
    const url = safeSourceUrl(reference.url);
    return url ? [{ ...reference, url }] : [];
  });
  return (
    <article
      className={`${styles.highlight} ${dossier.retention}`}
      aria-labelledby="project-retention"
      data-project-retention={retention.status}
    >
      <h3 id="project-retention">{labels.title}</h3>
      <dl className={dossier.retentionFacts}>
        <div>
          <dt>{labels.atDeclaredStage}</dt>
          <dd className={dossier.retentionRate}>
            {rates.length ? rates.join(` ${labels.or} `) : labels.unreadable}
          </dd>
          {rates.length > 0 && (
            <dd className={styles.muted}>{labels.ofPrice}</dd>
          )}
        </div>
        <div>
          <dt>{labels.declaredProgress}</dt>
          <dd>
            {retention.progress_percent === null
              ? projectLabels.notDocumented
              : formatPercent(retention.progress_percent, locale)}
            {" · "}
            {inspected && retention.progress_inspected_on ? (
              <>
                {labels.inspectedOn}{" "}
                <time dateTime={retention.progress_inspected_on}>
                  {inspected}
                </time>
              </>
            ) : (
              labels.inspectionUnknown
            )}
          </dd>
        </div>
      </dl>
      <Proof
        source={retention.progress_source}
        labels={projectLabels}
        locale={locale}
      />
      {retention.status === "boundary" && (
        <p className={styles.muted}>{labels.boundary}</p>
      )}
      {retention.full_refund_possible && (
        <p className={styles.muted}>{labels.fullRefund}</p>
      )}
      <p className={styles.muted}>
        {labels.paidShare}{" "}
        <strong>
          {formatPercent(retention.paid_share_discretion_percent, locale)}
        </strong>
      </p>
      <p className={styles.muted}>{labels.stageAssessed}</p>
      <details className={`${styles.proof} ${dossier.proof}`}>
        <summary>{labels.rule}</summary>
        <p lang="en" dir="ltr">
          <bdi>{retention.source.decision}</bdi>
        </p>
        {!retention.source.official_text_obtained && (
          <p>{labels.officialTextMissing}</p>
        )}
        <ul className={dossier.retentionReferences}>
          {references.map((reference) => (
            <li key={reference.url}>
              <a href={reference.url} target="_blank" rel="noopener noreferrer">
                <bdi>{reference.publisher}</bdi>{" "}
                <span aria-hidden="true">↗</span>
              </a>{" "}
              · {labels.publishedOn}{" "}
              <time dateTime={reference.published_on}>
                {formatProjectDate(reference.published_on, locale) ??
                  reference.published_on}
              </time>
              <SourceRights source={reference} labels={projectLabels} />
            </li>
          ))}
        </ul>
      </details>
      <p className={styles.muted}>{labels.notAdvice}</p>
    </article>
  );
}
