import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";
import { TerritoryExplorer } from "@/features/atlas/territory-explorer";
import type {
  AtlasLabels,
  CoverageLabels,
  MapLabels,
} from "@/features/atlas/types";
import { redirect } from "@/i18n/navigation";
import english from "../../../../messages/en.json";

export default async function ExplorePage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string; territory?: string }>;
}) {
  const t = await getTranslations("Atlas");
  const locale = await getLocale();
  const query = await searchParams;
  if (query.tab === "market")
    redirect({
      locale,
      href: {
        pathname: "/market",
        query: query.territory ? { territory: query.territory } : undefined,
      },
    });
  const messages = await getMessages();
  const map = await getTranslations("Map");
  const coverage = await getTranslations("Coverage");
  const coverageLabels = Object.fromEntries(
    Object.keys(english.Coverage).map((key) => [
      key,
      coverage(key as keyof typeof english.Coverage),
    ]),
  ) as CoverageLabels;
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
  return (
    <NextIntlClientProvider
      messages={{
        Context: messages.Context,
        Use: messages.Use,
        Project: messages.Project,
      }}
    >
      <div className="explore-viewport" data-page="explore">
        <TerritoryExplorer
          labels={labels}
          mapLabels={mapLabels}
          coverage={coverageLabels}
          locale={locale}
        />
      </div>
    </NextIntlClientProvider>
  );
}
