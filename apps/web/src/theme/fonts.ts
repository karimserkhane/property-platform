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
  manropeVietnamese: "/fonts/manrope-vietnamese-v20.woff2",
  cormorantVietnamese: "/fonts/cormorant-garamond-vietnamese-v21.woff2",
} as const;

const fontProfiles = {
  latin: [fontFiles.manropeLatin, fontFiles.cormorantLatin],
  cyrillic: [
    fontFiles.manropeLatin,
    fontFiles.manropeCyrillic,
    fontFiles.cormorantCyrillic,
  ],
  arabic: [fontFiles.manropeLatin, fontFiles.notoArabic],
  system: [fontFiles.manropeLatin],
  vietnamese: [
    fontFiles.manropeLatin,
    fontFiles.cormorantLatin,
    fontFiles.manropeVietnamese,
    fontFiles.cormorantVietnamese,
  ],
} as const;

export type FontProfile = keyof typeof fontProfiles;

export function getFontPreloads(profile: FontProfile): readonly FontPreload[] {
  return fontProfiles[profile].map((href) => ({ href, type: "font/woff2" }));
}
