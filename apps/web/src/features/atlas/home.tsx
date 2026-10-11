import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";

export async function AtlasHome() {
  const t = await getTranslations("Atlas");
  const home = await getTranslations("Home");
  return (
    <main className="home-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="status-dot" /> {t("pilot")} · <bdi>Abu Dhabi</bdi>
          </p>
          <h1>{home("title")}</h1>
          <p className="hero-description">{t("intro")}</p>
          <div className="hero-actions">
            <Link className="button" href="/explore">
              {t("explore")} <span aria-hidden="true">↗</span>
            </Link>
            <a className="text-link" href="#sources">
              {t("sources")}
            </a>
          </div>
        </div>
        <Link className="atlas-cover" href="/explore" aria-label={t("explore")}>
          <div className="cover-top">
            <span>LIWA / ATLAS</span>
            <span aria-hidden="true">24°29′ N · 54°25′ E</span>
          </div>
          <div className="cover-title">
            <span>AL REEM</span>
            <span>ISLAND</span>
          </div>
          <div className="cover-bottom">
            <span>{t("map")}</span>
            <span aria-hidden="true">↗</span>
          </div>
        </Link>
      </section>
      <section
        className="method-section"
        id="sources"
        aria-labelledby="sources-title"
      >
        <div>
          <p className="eyebrow">DMT / ONWANI</p>
          <h2 id="sources-title">{t("sources")}</h2>
        </div>
        <p>{t("limitations")}</p>
        <a
          className="text-link"
          href="https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/0"
          target="_blank"
          rel="noopener noreferrer"
        >
          {t("source")} ↗
        </a>
      </section>
    </main>
  );
}
