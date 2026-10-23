import { Link } from "@/i18n/navigation";
import dossier from "./dossier.module.css";
import { formatProjectDate, projectRelations } from "./presentation";
import styles from "./project.module.css";
import type { ProjectLabels } from "./types";

type Relation = ReturnType<typeof projectRelations>["components"][number];

/** Why two project pages are linked: reviewed basis, cited page and retrieval date. */
function RelationProof({
  relation,
  labels,
  locale,
}: {
  relation: Relation;
  labels: ProjectLabels;
  locale: string;
}) {
  const retrieved = formatProjectDate(relation.retrieved_at, locale);
  return (
    <details
      className={`${styles.proof} ${dossier.proof}`}
      data-project-evidence
    >
      <summary>{labels.sources}</summary>
      <p lang="en" dir="ltr">
        {relation.basis}
      </p>
      {relation.source_url && (
        <a href={relation.source_url} target="_blank" rel="noopener noreferrer">
          {labels.source} <span aria-hidden="true">↗</span>
        </a>
      )}
      {retrieved && (
        <p className={dossier.evidenceDate}>
          {labels.retrieved}{" "}
          <time dateTime={relation.retrieved_at}>{retrieved}</time>
        </p>
      )}
    </details>
  );
}

export function ProjectParent({
  project,
  labels,
  locale,
}: {
  project: Parameters<typeof projectRelations>[0];
  labels: ProjectLabels;
  locale: string;
}) {
  const { parent } = projectRelations(project);
  if (!parent) return null;
  return (
    <div className={`${styles.developer} ${dossier.parent}`}>
      <span>{labels.partOf}</span>
      <Link href={`/projects/${parent.slug}`}>
        <bdi>{parent.name}</bdi>
      </Link>
      <RelationProof relation={parent} labels={labels} locale={locale} />
    </div>
  );
}

export function ProjectComponents({
  project,
  labels,
  locale,
}: {
  project: Parameters<typeof projectRelations>[0];
  labels: ProjectLabels;
  locale: string;
}) {
  const { components } = projectRelations(project);
  if (!components.length) return null;
  return (
    <section className={styles.section} aria-labelledby="project-components">
      <div className={styles.sectionHeading}>
        <h2 id="project-components">{labels.components}</h2>
      </div>
      <p className={styles.muted}>{labels.relationNote}</p>
      <ul className={dossier.components}>
        {components.map((relation) => (
          <li className={dossier.component} key={relation.slug}>
            <Link href={`/projects/${relation.slug}`}>
              <bdi>{relation.name}</bdi> <span aria-hidden="true">↗</span>
            </Link>
            <p className={styles.muted}>
              <bdi>{relation.component}</bdi>
            </p>
            <RelationProof
              relation={relation}
              labels={labels}
              locale={locale}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}
