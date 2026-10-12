import { getLocale, getTranslations } from "next-intl/server";
import { Explorer } from "@/features/atlas/explorer";
import type { AtlasLabels, MapLabels } from "@/features/atlas/types";
import english from "../../../../messages/en.json";

export default async function ExplorePage() {
  const t = await getTranslations("Atlas");
  const locale = await getLocale();
  const map = await getTranslations("Map");
  const mapLabels = Object.fromEntries(
    Object.keys(english.Map).map((key) => [
      key,
      map(key as keyof typeof english.Map),
    ]),
  ) as MapLabels;
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
  return <Explorer labels={labels} mapLabels={mapLabels} locale={locale} />;
}
