import { getTranslations } from "next-intl/server";

export default async function HomePage() {
  const t = await getTranslations("Home");
  return (
    <main>
      <p className="eyebrow">
        <bdi>Liwa Atlas</bdi> · {t("location")}
      </p>
      <h1>{t("title")}</h1>
      <p>{t("description")}</p>
    </main>
  );
}
