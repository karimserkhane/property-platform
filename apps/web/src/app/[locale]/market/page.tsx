import { brand } from "@property-platform/branding";
import navigation from "@property-platform/contracts/territories";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations } from "next-intl/server";
import { AdrecMarket } from "@/features/atlas/adrec-market";
import styles from "@/features/atlas/market-page.module.css";
import type { MapLabels } from "@/features/atlas/types";
import { isLocale } from "@/i18n/locales";
import { Link } from "@/i18n/navigation";

type Props = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ territory?: string }>;
};
const areas = navigation.territories
  .filter((area) => area.queryable)
  .map((area) => area.id);

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = await getTranslations({ locale, namespace: "Market" });
  return { title: `${t("tab")} · ${brand.displayName}` };
}

export default async function MarketPage({ params, searchParams }: Props) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const { territory = "abu-dhabi" } = await searchParams;
  if (!areas.includes(territory)) notFound();
  const [messages, t, project, coverage] = await Promise.all([
    getMessages({ locale }),
    getTranslations({ locale, namespace: "Market" }),
    getTranslations({ locale, namespace: "Project" }),
    getTranslations({ locale, namespace: "Coverage" }),
  ]);
  const mapText = await getTranslations({ locale, namespace: "Map" });
  const mapLabels = Object.fromEntries(
    Object.keys(messages.Map).map((key) => [
      key,
      mapText(key as keyof typeof messages.Map),
    ]),
  ) as MapLabels;
  return (
    <main className={styles.page} data-page="market">
      <Link
        className={styles.back}
        href={{ pathname: "/explore", query: { territory } }}
      >
        ← {project("backToMap")}
      </Link>
      <header className={styles.heading}>
        <p>ADREC</p>
        <h1>{t("tab")}</h1>
      </header>
      <nav className={styles.areas} aria-label={coverage("area")}>
        {areas.map((id) => {
          const area = navigation.territories.find((item) => item.id === id);
          return (
            <Link
              key={id}
              aria-current={id === territory ? "page" : undefined}
              href={{ pathname: "/market", query: { territory: id } }}
            >
              <bdi>{locale === "ar" ? area?.name_ar : area?.name}</bdi>
            </Link>
          );
        })}
      </nav>
      <NextIntlClientProvider
        locale={locale}
        messages={{ Market: messages.Market }}
      >
        <AdrecMarket
          key={territory}
          territory={territory}
          locale={locale}
          mapLabels={mapLabels}
        />
      </NextIntlClientProvider>
    </main>
  );
}
