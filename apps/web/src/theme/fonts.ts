type FontPreload = Readonly<{
  href: string;
  type: "font/woff2";
}>;

const fontFiles = {
  manropeLatin: "/fonts/manrope-latin-v20.woff2",
  manropeCyrillic: "/fonts/manrope-cyrillic-v20.woff2",
  cormorantLatin: "/fonts/cormorant-garamond-latin-v21.woff2",
  cormorantCyrillic: "/fonts/cormorant-garamond-cyrillic-v21.woff2",
  notoArabic: "/fonts/noto-sans-arabic-v33.woff2",
} as const;

const latinInterfaceLocales = new Set(["en", "es", "de", "fil", "fr", "pt"]);

export function getFontPreloads(locale: string): readonly FontPreload[] {
  const files: string[] = [fontFiles.manropeLatin];
  if (latinInterfaceLocales.has(locale)) files.push(fontFiles.cormorantLatin);
  if (locale === "ru") {
    files.push(fontFiles.manropeCyrillic, fontFiles.cormorantCyrillic);
  }
  if (locale === "ar" || locale === "ur" || locale === "fa") {
    files.push(fontFiles.notoArabic);
  }
  return files.map((href) => ({ href, type: "font/woff2" }));
}
