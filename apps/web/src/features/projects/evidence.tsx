import dossier from "./dossier.module.css";
import {
  formatProjectDate,
  projectEvidenceSources,
  safeSourceUrl,
} from "./presentation";
import styles from "./project.module.css";
import type { ProjectLabels, ProjectSource } from "./types";

export function SourceLink({
  source,
  labels,
  showDeveloper = false,
}: {
  source: ProjectSource;
  labels: ProjectLabels;
  showDeveloper?: boolean;
}) {
  const url = safeSourceUrl(source.url);
  return url ? (
    <>
      <a href={url} target="_blank" rel="noopener noreferrer">
        {labels.source} · <bdi>{source.name}</bdi>{" "}
        <span aria-hidden="true">↗</span>
      </a>
      {showDeveloper && source.developer_name && (
        <p className={styles.muted}>
          {source.developer_role === "registered"
            ? labels.registeredDeveloper
            : labels.declaredDeveloper}{" "}
          · <bdi>{source.developer_name}</bdi>
        </p>
      )}
      {source.historical && <small> · {labels.historical}</small>}
    </>
  ) : null;
}

/** A source citation explains provenance, without rendering extractor payloads. */
export function Proof({
  source,
  labels,
  locale,
}: {
  source: ProjectSource;
  labels: ProjectLabels;
  locale: string;
}) {
  return (
    <details
      className={`${styles.proof} ${dossier.proof}`}
      data-project-evidence
    >
      <summary>{labels.sources}</summary>
      <SourceCitation source={source} labels={labels} locale={locale} />
    </details>
  );
}

function SourceCitation({
  source,
  labels,
  locale,
}: {
  source: ProjectSource;
  labels: ProjectLabels;
  locale: string;
}) {
  const retrieved = formatProjectDate(source.retrieved_at, locale);
  return (
    <div data-project-evidence-source>
      <SourceLink source={source} labels={labels} />
      {retrieved && (
        <p className={dossier.evidenceDate}>
          {labels.retrieved}{" "}
          <time dateTime={source.retrieved_at}>{retrieved}</time>
        </p>
      )}
    </div>
  );
}

export function ProofGroup({
  sources,
  labels,
  locale,
}: {
  sources: ProjectSource[];
  labels: ProjectLabels;
  locale: string;
}) {
  const evidence = projectEvidenceSources(sources);
  return (
    <details
      className={`${styles.proof} ${dossier.proof}`}
      data-project-evidence
    >
      <summary>{labels.sources}</summary>
      <ul className={dossier.claims}>
        {evidence.map(({ key, source }) => (
          <li key={key}>
            <SourceCitation source={source} labels={labels} locale={locale} />
          </li>
        ))}
      </ul>
    </details>
  );
}
