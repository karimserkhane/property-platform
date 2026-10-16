import type { FontProfile } from "../theme/fonts";

export const localeDefinitions = {
  en: { name: "English", direction: "ltr", fontProfile: "latin" },
  ar: { name: "العربية", direction: "rtl", fontProfile: "arabic" },
  es: { name: "Español", direction: "ltr", fontProfile: "latin" },
  de: { name: "Deutsch", direction: "ltr", fontProfile: "latin" },
  ru: { name: "Русский", direction: "ltr", fontProfile: "cyrillic" },
  hi: { name: "हिन्दी", direction: "ltr", fontProfile: "system" },
  ur: { name: "اردو", direction: "rtl", fontProfile: "arabic" },
  bn: { name: "বাংলা", direction: "ltr", fontProfile: "system" },
  ml: { name: "മലയാളം", direction: "ltr", fontProfile: "system" },
  ta: { name: "தமிழ்", direction: "ltr", fontProfile: "system" },
  fil: { name: "Filipino", direction: "ltr", fontProfile: "latin" },
  fa: { name: "فارسی", direction: "rtl", fontProfile: "arabic" },
  zh: { name: "中文", direction: "ltr", fontProfile: "system" },
  fr: { name: "Français", direction: "ltr", fontProfile: "latin" },
  pt: { name: "Português", direction: "ltr", fontProfile: "latin" },
  vi: { name: "Tiếng Việt", direction: "ltr", fontProfile: "vietnamese" },
} as const satisfies Record<
  string,
  { name: string; direction: "ltr" | "rtl"; fontProfile: FontProfile }
>;

export type Locale = keyof typeof localeDefinitions;
export const locales = Object.keys(localeDefinitions) as Locale[];
export const defaultLocale: Locale = "en";

export function isLocale(value: string): value is Locale {
  return Object.hasOwn(localeDefinitions, value);
}

export function getDirection(locale: Locale) {
  return localeDefinitions[locale].direction;
}
