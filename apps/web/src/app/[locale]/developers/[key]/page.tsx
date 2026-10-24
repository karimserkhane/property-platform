import { brand } from "@property-platform/branding";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import type { DeliveryLabels } from "@/features/projects/delivery";
import { DeliveryHistoryView } from "@/features/projects/delivery-history";
import { readDeliveryHistory } from "@/features/projects/server";
import type { ProjectLabels } from "@/features/projects/types";
import { isLocale } from "@/i18n/locales";
import { Link } from "@/i18n/navigation";
import english from "../../../../../messages/en.json";

type DeveloperPageProps = {
  params: Promise<{ locale: string; key: string }>;
};

export async function generateMetadata({
  params,
}: DeveloperPageProps): Promise<Metadata> {
  const { locale, key } = await params;
  if (!isLocale(locale)) return {};
  const t = await getTranslations({ locale, namespace: "Delivery" });
  const result = await readDeliveryHistory(key);
  return result.history
    ? {
        title: `${result.history.developer.name} · ${t("title")} · ${brand.displayName}`,
      }
    : {};
}

export default async function DeveloperDeliveryPage({
  params,
}: DeveloperPageProps) {
  const { locale, key } = await params;
  if (!isLocale(locale)) notFound();
  const project = await getTranslations({ locale, namespace: "Project" });
  const delivery = await getTranslations({ locale, namespace: "Delivery" });
  const result = await readDeliveryHistory(key);
  if (result.status === 404) notFound();
  if (!result.history)
    return (
      <main className="explore-shell">
        <h1>{project("unavailableTitle")}</h1>
        <p role="status">{project("unavailable")}</p>
        <Link className="button" href="/projects">
          {project("projects")}
        </Link>
      </main>
    );
  const projectLabels = Object.fromEntries(
    Object.keys(english.Project).map((name) => [
      name,
      project(name as keyof typeof english.Project),
    ]),
  ) as ProjectLabels;
  const labels = Object.fromEntries(
    Object.keys(english.Delivery).map((name) => [
      name,
      delivery(name as keyof typeof english.Delivery),
    ]),
  ) as DeliveryLabels;
  return (
    <DeliveryHistoryView
      history={result.history}
      locale={locale}
      labels={labels}
      projectLabels={projectLabels}
    />
  );
}
