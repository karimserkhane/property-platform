import type { components } from "@property-platform/contracts";
import navigation from "@property-platform/contracts/territories";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { readPreview } from "@/features/atlas/server";
import { ProjectDirectoryList } from "@/features/projects/directory";
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
      <header className={styles.directoryHeading}>
        <p className={styles.kicker}>
          {["al-reem-island", "saadiyat-island"].map(areaName).join(" / ")}
        </p>
        <h1>{t("projects")}</h1>
        <p className={styles.directoryIntro}>{t("directoryIntro")}</p>
      </header>
      <nav className={styles.areaNav} aria-label={t("location")}>
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
        <ProjectDirectoryList
          key={territory ?? "all"}
          projects={data.items.map((project) => ({
            ...project,
            areaName: areaName(project.territory),
          }))}
          locale={locale}
          hasMore={data.has_more}
          labels={{
            projects: t("projects"),
            viewDetails: t("viewDetails"),
            searchProjects: t("searchProjects"),
            searchPlaceholder: t("searchPlaceholder"),
            clearSearch: t("clearSearch"),
            noProjects: t("noProjects"),
            noProjectsHint: t("noProjectsHint"),
            openPage: t("openPage"),
          }}
        />
      ) : (
        <p role="status">{t("unavailable")}</p>
      )}
    </main>
  );
}
