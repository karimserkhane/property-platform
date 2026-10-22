import type { components } from "@property-platform/contracts";
import navigation from "@property-platform/contracts/territories";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { readPreview } from "@/features/atlas/server";
import { ProjectDirectoryList } from "@/features/projects/directory";
import styles from "@/features/projects/directory.module.css";
import {
  availableDirectoryOffset,
  PROJECT_DIRECTORY_PAGE_SIZE,
  projectDirectoryHref,
} from "@/features/projects/directory-navigation";
import { isLocale } from "@/i18n/locales";
import { Link, redirect } from "@/i18n/navigation";

const areas = navigation.territories
  .filter((area) => area.level === "area" && area.queryable)
  .map((area) => area.id);

export default async function ProjectDirectory({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ territory?: string; q?: string; offset?: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const { territory, q = "", offset: rawOffset = "0" } = await searchParams;
  if (territory !== undefined && !areas.includes(territory)) notFound();
  if (
    typeof q !== "string" ||
    q.length > 120 ||
    typeof rawOffset !== "string" ||
    !/^(0|[1-9]\d{0,4})$/.test(rawOffset) ||
    Number(rawOffset) > 50000
  )
    notFound();
  const offset = Number(rawOffset);
  const t = await getTranslations({ locale, namespace: "Project" });
  const map = await getTranslations({ locale, namespace: "Map" });
  const atlas = await getTranslations({ locale, namespace: "Atlas" });
  const pagination = await getTranslations({ locale, namespace: "Context" });
  let data: components["schemas"]["ProjectDirectoryResponse"] | null = null;
  try {
    const response = await readPreview(
      "projects",
      `?${new URLSearchParams({ ...(territory ? { territory } : {}), q, offset: String(offset), limit: String(PROJECT_DIRECTORY_PAGE_SIZE) })}`,
    );
    if (response.status === 200)
      data = response.data as components["schemas"]["ProjectDirectoryResponse"];
  } catch {
    /* The same translated unavailable state covers a transport failure. */
  }
  if (data && availableDirectoryOffset(offset, data.total) !== offset)
    redirect({
      locale,
      href: projectDirectoryHref({
        territory,
        query: q,
        offset: availableDirectoryOffset(offset, data.total),
      }),
    });
  const areaName = (id: string) => {
    const area = navigation.territories.find((item) => item.id === id);
    return area ? (locale === "ar" ? area.name_ar : area.name) : id;
  };
  return (
    <main className={styles.page} data-page="project-directory">
      <header className={styles.heading}>
        <p className={styles.kicker}>{areas.map(areaName).join(" / ")}</p>
        <h1>{t("projects")}</h1>
        <p className={styles.intro}>{t("directoryIntro")}</p>
      </header>
      <nav className={styles.areaNav} aria-label={t("location")}>
        <Link
          href={projectDirectoryHref({ query: q })}
          aria-current={territory === undefined ? "page" : undefined}
        >
          {t("allProjects")}
        </Link>
        {areas.map((id) => (
          <Link
            key={id}
            href={projectDirectoryHref({ territory: id, query: q })}
            aria-current={territory === id ? "page" : undefined}
          >
            <bdi>{areaName(id)}</bdi>
          </Link>
        ))}
      </nav>
      {data ? (
        <ProjectDirectoryList
          key={`${territory ?? "all"}:${q}:${offset}`}
          projects={data.items.map((project) => ({
            ...project,
            areaName: areaName(project.territory),
          }))}
          locale={locale}
          hasMore={data.has_more}
          total={data.total}
          offset={data.offset}
          initialQuery={q}
          territory={territory}
          labels={{
            projects: t("projects"),
            viewDetails: t("viewDetails"),
            searchProjects: t("searchProjects"),
            submitSearch: atlas("search"),
            searchPlaceholder: t("searchPlaceholder"),
            clearSearch: t("clearSearch"),
            noProjects: t("noProjects"),
            noProjectsHint: t("noProjectsHint"),
            locate: map("locate"),
            mapLocationPending: t("notMapped"),
            previous: pagination("previous"),
            next: pagination("next"),
            pages: pagination("pages"),
          }}
        />
      ) : (
        <div className={styles.emptyState} role="status">
          <h2>{t("unavailable")}</h2>
          <a
            className={styles.clearSearch}
            href={`/${locale}/projects?${new URLSearchParams({ ...(territory ? { territory } : {}), ...(q ? { q } : {}) })}`}
          >
            {t("retry")}
          </a>
        </div>
      )}
    </main>
  );
}
