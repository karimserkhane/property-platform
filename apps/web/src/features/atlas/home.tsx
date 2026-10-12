import { brand } from "@property-platform/branding";
import navigation from "@property-platform/contracts/territories";
import { getLocale, getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import styles from "./home.module.css";
import { HomeGallery } from "./home-gallery";
import type { GalleryLabels } from "./home-scenes";

export async function AtlasHome() {
  const t = await getTranslations("Atlas");
  const home = await getTranslations("Home");
  const map = await getTranslations("Map");
  const coverage = await getTranslations("Coverage");
  const locale = await getLocale();
  const galleryLabels = Object.fromEntries(
    (
      [
        "galleryLabel",
        "photoCredit",
        "night",
        "coast",
        "sunset",
        "pause",
        "play",
      ] as const
    ).map((key) => [key, home(key)]),
  ) as GalleryLabels;
  return (
    <main className={styles.page} data-page="home">
      <section className={styles.hero} aria-labelledby="home-title">
        <HomeGallery labels={galleryLabels} />
        <div className={styles.heroCopy}>
          <p className={styles.eyebrow}>
            <span aria-hidden="true" /> {home("eyebrow")}
          </p>
          <h1 id="home-title" className={styles.title}>
            {home("title")}
          </h1>
          <p className={styles.description}>{home("description")}</p>
          <div className={styles.actions}>
            <Link className={styles.primaryAction} href="/explore">
              {t("explore")} <span aria-hidden="true">↗</span>
            </Link>
            <a className={styles.secondaryAction} href="#sources">
              {t("sources")}
            </a>
          </div>
          <p className={styles.coverage}>{home("coverage")}</p>
        </div>
      </section>
      <section className={styles.regions} aria-labelledby="regions-title">
        <p className={styles.sectionEyebrow}>{home("location")}</p>
        <h2 id="regions-title">{coverage("title")}</h2>
        <p className={styles.regionNote}>{home("coverage")}</p>
        <div className={styles.regionGrid}>
          {navigation.territories
            .filter((territory) => territory.level === "emirate")
            .map((territory) => {
              const pilot = navigation.territories.find(
                (area) => area.parent_id === territory.id && area.queryable,
              );
              return (
                <Link
                  key={territory.id}
                  className={styles.regionCard}
                  href={{
                    pathname: "/explore",
                    query: { territory: pilot?.id ?? territory.id },
                  }}
                >
                  <bdi>
                    {locale === "ar" ? territory.name_ar : territory.name}
                  </bdi>
                  <span>
                    {pilot ? coverage("visitPilot") : coverage("preparing")}
                  </span>
                  <span aria-hidden="true">↗</span>
                </Link>
              );
            })}
        </div>
      </section>
      <section className={styles.discovery} aria-labelledby="discovery-title">
        <div className={styles.discoveryCopy}>
          <p className={styles.sectionEyebrow}>
            <bdi>{brand.displayName}</bdi> / <bdi>{home("location")}</bdi>
          </p>
          <h2 id="discovery-title">{home("discoverTitle")}</h2>
          <p>{home("discoverBody")}</p>
        </div>
        <div className={styles.layerLinks}>
          {[map("parcels"), map("streets"), map("buildings"), t("sources")].map(
            (label, index) => (
              <Link key={label} href="/explore" className={styles.layerLink}>
                <span className={styles.layerIndex} aria-hidden="true">
                  0{index + 1}
                </span>
                <span>{label}</span>
                <span className={styles.layerArrow} aria-hidden="true">
                  ↗
                </span>
              </Link>
            ),
          )}
        </div>
      </section>
      <section
        className={styles.sources}
        id="sources"
        aria-labelledby="sources-title"
      >
        <div>
          <p className={styles.sectionEyebrow}>DMT / ONWANI + OPENSTREETMAP</p>
          <h2 id="sources-title">{t("sources")}</h2>
        </div>
        <p>{t("limitations")}</p>
        <a
          className={styles.sourceAction}
          href="https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer/0"
          target="_blank"
          rel="noopener noreferrer"
        >
          {t("source")} ↗
        </a>
      </section>
      <footer className={styles.footer}>
        <bdi>{brand.displayName}</bdi>
        <span>{t("pilot")}</span>
      </footer>
    </main>
  );
}
