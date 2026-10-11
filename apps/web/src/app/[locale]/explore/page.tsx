import { getLocale, getTranslations } from "next-intl/server";
import { Explorer } from "@/features/atlas/explorer";
import type { AtlasLabels } from "@/features/atlas/types";

export default async function ExplorePage() {
  const t = await getTranslations("Atlas");
  const locale = await getLocale();
  const keys = [
    "explore",
    "sources",
    "pilot",
    "intro",
    "search",
    "reference",
    "loading",
    "unavailable",
    "retry",
    "empty",
    "truncated",
    "select",
    "source",
    "retrieved",
    "published",
    "unknown",
    "district",
    "community",
    "limitations",
    "list",
    "map",
    "reset",
    "count",
    "back",
  ] as const;
  const labels = Object.fromEntries(
    keys.map((key) => [key, t(key)]),
  ) as AtlasLabels;
  return <Explorer labels={labels} locale={locale} />;
}
