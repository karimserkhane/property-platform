import dossier from "./dossier.module.css";
import { MediaCard } from "./media-card";
import styles from "./project.module.css";
import type { ProjectLabels, ProjectMedia } from "./types";

export function ProjectDocuments({
  documents,
  labels,
  locale,
}: {
  documents: ProjectMedia[];
  labels: ProjectLabels;
  locale: string;
}) {
  const plans = documents.filter((item) => item.role === "floor_plan");
  const other = documents.filter((item) => item.role !== "floor_plan");
  return (
    <section className={styles.section} aria-labelledby="project-documents">
      <div className={styles.sectionHeading}>
        <h2 id="project-documents">{labels.documents}</h2>
        {documents.length > 0 && (
          <span>{new Intl.NumberFormat(locale).format(documents.length)}</span>
        )}
      </div>
      <div className={dossier.documentGroups}>
        <div>
          <h3 className={dossier.documentGroupTitle}>{labels.floorPlans}</h3>
          {plans.length ? (
            <div className={styles.media}>
              {plans.map((item) => (
                <MediaCard
                  key={item.id}
                  media={item}
                  labels={labels}
                  locale={locale}
                />
              ))}
            </div>
          ) : (
            <p className={dossier.documentEmpty}>{labels.notDocumented}</p>
          )}
        </div>
        {other.length > 0 && (
          <div className={styles.media}>
            {other.map((item) => (
              <MediaCard
                key={item.id}
                media={item}
                labels={labels}
                locale={locale}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
