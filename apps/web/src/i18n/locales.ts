export const localeDefinitions = {
  en: { name: "English", direction: "ltr" },
  ar: { name: "العربية", direction: "rtl" },
  es: { name: "Español", direction: "ltr" },
  de: { name: "Deutsch", direction: "ltr" },
  ru: { name: "Русский", direction: "ltr" },
  hi: { name: "हिन्दी", direction: "ltr" },
  ur: { name: "اردو", direction: "rtl" },
  bn: { name: "বাংলা", direction: "ltr" },
  ml: { name: "മലയാളം", direction: "ltr" },
  ta: { name: "தமிழ்", direction: "ltr" },
  fil: { name: "Filipino", direction: "ltr" },
  fa: { name: "فارسی", direction: "rtl" },
  zh: { name: "中文", direction: "ltr" },
  fr: { name: "Français", direction: "ltr" },
  pt: { name: "Português", direction: "ltr" },
} as const;

export type Locale = keyof typeof localeDefinitions;
export const locales = Object.keys(localeDefinitions) as Locale[];
export const defaultLocale: Locale = "en";

export function isLocale(value: string): value is Locale {
  return Object.hasOwn(localeDefinitions, value);
}

export function getDirection(locale: Locale) {
  return localeDefinitions[locale].direction;
}
