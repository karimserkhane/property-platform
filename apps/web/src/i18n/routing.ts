import { defineRouting } from "next-intl/routing";
import { defaultLocale, locales } from "./locales";

export const routing = defineRouting({
  locales,
  defaultLocale,
  localePrefix: "always",
  // The user explicitly requested English by default, regardless of browser language.
  localeDetection: false,
  localeCookie: false,
});
