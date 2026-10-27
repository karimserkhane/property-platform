import { brand } from "@property-platform/branding";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import type { SourcesLabels } from "@/features/sources/data";
import { readSourceSites } from "@/features/sources/server";
import { SourcesView } from "@/features/sources/sources-view";
import { isLocale } from "@/i18n/locales";
import { Link } from "@/i18n/navigation";
import english from "../../../../messages/en.json";

type SourcesPageProps = { params: Promise<{ locale: string }> };

export async function generateMetadata({
  params,
}: SourcesPageProps): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) return {};
  const t = await getTranslations({ locale, namespace: "Sources" });
  return { title: `${t("title")} · ${brand.displayName}` };
}

export default async function SourcesPage({ params }: SourcesPageProps) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const project = await getTranslations({ locale, namespace: "Project" });
  const t = await getTranslations({ locale, namespace: "Sources" });
  const result = await readSourceSites();
  if (!result.sites)
    return (
      <main className="explore-shell">
        <h1>{project("unavailableTitle")}</h1>
        <p role="status">{project("unavailable")}</p>
        <Link className="button" href="/projects">
          {project("projects")}
        </Link>
      </main>
    );
  const labels = Object.fromEntries(
    Object.keys(english.Sources)
      .filter((name) => name !== "reviewedCount")
      .map((name) => [name, t(name as keyof SourcesLabels)]),
  ) as SourcesLabels;
  return (
    <SourcesView
      sites={result.sites}
      count={t("reviewedCount", {
        reviewed: result.sites.filter((site) => site.reviewed_on).length,
        total: result.sites.length,
      })}
      locale={locale}
      labels={labels}
      licenceLabels={{
        projects: project("projects"),
        navigation: project("navigation"),
        rightsUnreviewed: project("rightsUnreviewed"),
        rightsReserved: project("rightsReserved"),
        rightsPerItem: project("rightsPerItem"),
        rightsTerms: project("rightsTerms"),
      }}
    />
  );
}
