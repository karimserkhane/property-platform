import { brand } from "@property-platform/branding";
import navigation from "@property-platform/contracts/territories";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import type { MapLabels } from "@/features/atlas/types";
import { ProjectDetailView } from "@/features/projects/detail";
import { ProjectNeighbourhood } from "@/features/projects/neighbourhood";
import { googleNeighbourhoodUrl } from "@/features/projects/neighbourhood-config";
import { readProject } from "@/features/projects/server";
import type { ProjectLabels } from "@/features/projects/types";
import { isLocale } from "@/i18n/locales";
import { Link } from "@/i18n/navigation";
import english from "../../../../../messages/en.json";

type ProjectPageProps = {
  params: Promise<{ locale: string; slug: string }>;
};

export async function generateMetadata({
  params,
}: ProjectPageProps): Promise<Metadata> {
  const { slug } = await params;
  const result = await readProject(slug);
  return result.project
    ? { title: `${result.project.name} · ${brand.displayName}` }
    : {};
}

export default async function ProjectPage({ params }: ProjectPageProps) {
  const { locale, slug } = await params;
  if (!isLocale(locale)) notFound();
  const t = await getTranslations({ locale, namespace: "Project" });
  const result = await readProject(slug);
  if (result.status === 404) notFound();
  if (!result.project)
    return (
      <main className="explore-shell">
        <h1>{t("unavailableTitle")}</h1>
        <p role="status">{t("unavailable")}</p>
        <Link className="button" href="/explore">
          {t("backToMap")}
        </Link>
      </main>
    );
  const labels = Object.fromEntries(
    Object.keys(english.Project).map((key) => [
      key,
      t(key as keyof typeof english.Project),
    ]),
  ) as ProjectLabels;
  const area = navigation.territories.find(
    (item) =>
      item.id === result.project?.territory &&
      item.level === "area" &&
      item.queryable,
  );
  const mapText = await getTranslations({ locale, namespace: "Map" });
  const mapLabels = Object.fromEntries(
    Object.keys(english.Map).map((key) => [
      key,
      mapText(key as keyof typeof english.Map),
    ]),
  ) as MapLabels;
  return (
    <ProjectDetailView
      project={result.project}
      locale={locale}
      labels={labels}
      neighbourhood={
        area ? (
          <ProjectNeighbourhood
            key={`${locale}:${area.id}`}
            territory={area.id}
            bounds={area.bounds}
            slug={result.project.slug}
            locations={result.project.map_locations}
            locale={locale}
            labels={labels}
            mapLabels={mapLabels}
            googleUrl={googleNeighbourhoodUrl(
              area.bounds,
              locale,
              process.env.PROJECT_NEIGHBOURHOOD_PROVIDER,
              process.env.GOOGLE_MAPS_EMBED_BROWSER_KEY,
            )}
          />
        ) : undefined
      }
    />
  );
}
