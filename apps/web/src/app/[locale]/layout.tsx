import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { LanguageSwitcher } from "@/components/language-switcher";
import { getDirection, isLocale, locales } from "@/i18n/locales";
import { Link } from "@/i18n/navigation";
import "../globals.css";

type Props = {
  children: ReactNode;
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = await getTranslations({ locale, namespace: "Home" });
  return {
    title: "Liwa Atlas",
    description: t("description"),
    robots: { index: false, follow: false },
  };
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const messages = await getMessages({ locale });
  const home = await getTranslations({ locale, namespace: "Home" });

  return (
    <html lang={locale} dir={getDirection(locale)}>
      <body>
        <NextIntlClientProvider
          locale={locale}
          timeZone="Asia/Dubai"
          messages={{ LanguageSwitcher: messages.LanguageSwitcher }}
        >
          <header className="site-header">
            <Link className="brand" href="/" aria-label="Liwa Atlas">
              <svg
                className="brand-mark"
                viewBox="0 0 32 32"
                aria-hidden="true"
              >
                <path d="M7 6v20h19M7 16h12V6M19 16v10M7 6h12" />
              </svg>
              <bdi>Liwa Atlas</bdi>
            </Link>
            <div className="header-tools">
              <nav className="header-nav">
                <Link href="/explore">{home("navExplore")}</Link>
                <Link href="/#sources">{home("navSources")}</Link>
              </nav>
              <LanguageSwitcher />
            </div>
          </header>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
