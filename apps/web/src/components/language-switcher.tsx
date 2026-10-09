"use client";

import { useLocale, useTranslations } from "next-intl";
import { useTransition } from "react";
import { isLocale, localeDefinitions, locales } from "@/i18n/locales";
import { usePathname, useRouter } from "@/i18n/navigation";

export function LanguageSwitcher() {
  const locale = useLocale();
  const t = useTranslations("LanguageSwitcher");
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  return (
    <label className="language-switcher">
      <span>{t("label")}</span>
      <select
        value={locale}
        disabled={isPending}
        onChange={(event) => {
          const selectedLocale = event.currentTarget.value;
          if (!isLocale(selectedLocale)) return;
          const destination = `${pathname}${window.location.search}${window.location.hash}`;
          startTransition(() => {
            router.replace(destination, { locale: selectedLocale });
          });
        }}
      >
        {locales.map((code) => (
          <option
            key={code}
            value={code}
            lang={code}
            dir={localeDefinitions[code].direction}
          >
            {localeDefinitions[code].name}
          </option>
        ))}
      </select>
    </label>
  );
}
