import { brand } from "@property-platform/branding";
import navigation from "@property-platform/contracts/territories";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import type { MapLabels, UseLabels } from "@/features/atlas/types";
import type { ActivityLabels } from "@/features/projects/activity";
import type { DeliveryLabels } from "@/features/projects/delivery";
import { ProjectDetailView } from "@/features/projects/detail";
import { ProjectNeighbourhood } from "@/features/projects/neighbourhood";
import { googleNeighbourhoodUrl } from "@/features/projects/neighbourhood-config";
import type { RetentionLabels } from "@/features/projects/retention";
import type { ScheduleLabels } from "@/features/projects/schedule-form";
import { readProject } from "@/features/projects/server";
import type { ProjectLabels } from "@/features/projects/types";
import type { VerificationLabels } from "@/features/projects/verification";
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
  const usageText = await getTranslations({ locale, namespace: "Use" });
  const atlasText = await getTranslations({ locale, namespace: "Atlas" });
  const retentionText = await getTranslations({
    locale,
    namespace: "Retention",
  });
  const retentionLabels = Object.fromEntries(
    Object.keys(english.Retention).map((key) => [
      key,
      retentionText(key as keyof typeof english.Retention),
    ]),
  ) as RetentionLabels;
  const verificationText = await getTranslations({
    locale,
    namespace: "Verification",
  });
  const verificationLabels = Object.fromEntries(
    Object.keys(english.Verification).map((key) => [
      key,
      verificationText(key as keyof typeof english.Verification),
    ]),
  ) as VerificationLabels;
  const activityText = await getTranslations({ locale, namespace: "Activity" });
  const activityLabels = Object.fromEntries(
    Object.keys(english.Activity).map((key) => [
      key,
      activityText(key as keyof typeof english.Activity),
    ]),
  ) as ActivityLabels;
  const deliveryText = await getTranslations({ locale, namespace: "Delivery" });
  const deliveryLabels = Object.fromEntries(
    Object.keys(english.Delivery).map((key) => [
      key,
      deliveryText(key as keyof typeof english.Delivery),
    ]),
  ) as DeliveryLabels;
  const scheduleText = await getTranslations({ locale, namespace: "Schedule" });
  const scheduleLabels = Object.fromEntries(
    Object.keys(english.Schedule).map((key) => [
      key,
      scheduleText(key as keyof typeof english.Schedule),
    ]),
  ) as ScheduleLabels;
  const useLabels = Object.fromEntries(
    Object.keys(english.Use).map((key) => [
      key,
      usageText(key as keyof typeof english.Use),
    ]),
  ) as UseLabels;
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
      retentionLabels={retentionLabels}
      verificationLabels={verificationLabels}
      activityLabels={activityLabels}
      deliveryLabels={deliveryLabels}
      scheduleLabels={scheduleLabels}
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
            useLabels={useLabels}
            truncatedLabel={atlasText("truncated")}
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
