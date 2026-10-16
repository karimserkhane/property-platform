import type { components } from "@property-platform/contracts";
import navigation from "@property-platform/contracts/territories";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { readPreview } from "@/features/atlas/server";
import styles from "@/features/projects/project.module.css";
import { isLocale } from "@/i18n/locales";
import { Link } from "@/i18n/navigation";

export default async function ProjectDirectory({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ territory?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const { territory } = await searchParams;
  if (
    territory !== undefined &&
    !["al-reem-island", "saadiyat-island"].includes(territory)
  )
    notFound();
  const t = await getTranslations({ locale, namespace: "Project" });
  let data: components["schemas"]["ProjectDirectoryResponse"] | null = null;
  try {
    const response = await readPreview(
      "projects",
      territory ? `?territory=${territory}` : "",
    );
    if (response.status === 200)
      data = response.data as components["schemas"]["ProjectDirectoryResponse"];
  } catch {
    /* The same translated unavailable state covers a transport failure. */
  }
  const areaName = (id: string) => {
    const area = navigation.territories.find((item) => item.id === id);
    return area ? (locale === "ar" ? area.name_ar : area.name) : id;
  };
  return (
    <main className={styles.page} data-page="project-directory">
      <nav className={styles.breadcrumb} aria-label={t("navigation")}>
        <Link href="/explore">← {t("backToMap")}</Link>
      </nav>
      <div className={styles.directoryHeading}>
        <p className={styles.kicker}>
          {["al-reem-island", "saadiyat-island"].map(areaName).join(" / ")}
        </p>
        <h1>{t("projects")}</h1>
      </div>
      <nav className={styles.sectionNav} aria-label={t("location")}>
        <Link
          href="/projects"
          aria-current={territory === undefined ? "page" : undefined}
        >
          {t("allProjects")}
        </Link>
        {["al-reem-island", "saadiyat-island"].map((id) => (
          <Link
            key={id}
            href={{ pathname: "/projects", query: { territory: id } }}
            aria-current={territory === id ? "page" : undefined}
          >
            <bdi>{areaName(id)}</bdi>
          </Link>
        ))}
      </nav>
      {data ? (
        <>
          <p className={styles.muted}>
            {new Intl.NumberFormat(locale).format(data.items.length)}
            {data.has_more ? "+" : ""} · {t("projects")}
          </p>
          <div className={styles.directoryGrid}>
            {data.items.map((project) => (
              <article className={styles.directoryCard} key={project.id}>
                <p className={styles.kicker}>
                  <bdi>{areaName(project.territory)}</bdi>
                </p>
                <h2>
                  <Link href={`/projects/${project.slug}`}>
                    <bdi>{project.name}</bdi>
                  </Link>
                </h2>
                <p>
                  <bdi>{project.developer.name}</bdi>
                </p>
                {!project.has_map_identity && (
                  <p className={styles.muted}>{t("notMapped")}</p>
                )}
                <Link
                  className={styles.textAction}
                  href={`/projects/${project.slug}`}
                >
                  {t("viewDetails")} ↗
                </Link>
              </article>
            ))}
          </div>
        </>
      ) : (
        <p role="status">{t("unavailable")}</p>
      )}
    </main>
  );
}
