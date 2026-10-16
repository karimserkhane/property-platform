import { brand } from "@property-platform/branding";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { BrandMark } from "@/components/brand-mark";
import { LanguageSwitcher } from "@/components/language-switcher";
import { getDirection, isLocale, locales } from "@/i18n/locales";
import { Link } from "@/i18n/navigation";
import { getFontPreloads } from "@/theme/fonts";
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
    title: brand.displayName,
    icons: { icon: brand.webMarkPath },
    description: t("description"),
    openGraph: {
      title: brand.displayName,
      siteName: brand.displayName,
      description: t("description"),
      type: "website",
    },
    robots: { index: false, follow: false },
  };
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const messages = await getMessages({ locale });
  const home = await getTranslations({ locale, namespace: "Home" });
  const project = await getTranslations({ locale, namespace: "Project" });

  return (
    <html
      lang={locale}
      dir={getDirection(locale)}
      data-scroll-behavior="smooth"
    >
      <head>
        {getFontPreloads(locale).map((font) => (
          <link
            key={font.href}
            rel="preload"
            href={font.href}
            as="font"
            type={font.type}
            crossOrigin="anonymous"
          />
        ))}
      </head>
      <body>
        <NextIntlClientProvider
          locale={locale}
          timeZone="Asia/Dubai"
          messages={{ LanguageSwitcher: messages.LanguageSwitcher }}
        >
          <header className="site-header">
            <Link className="brand" href="/" aria-label={brand.displayName}>
              <BrandMark />
              <bdi>{brand.displayName}</bdi>
            </Link>
            <div className="header-tools">
              <nav className="header-nav">
                <Link href="/explore">{home("navExplore")}</Link>
                <Link href="/projects">{project("projects")}</Link>
                <Link href="/#regions">{home("navLocations")}</Link>
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
