import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import styles from "./home.module.css";
import { HomeGallery } from "./home-gallery";
import type { GalleryLabels } from "./home-scenes";

export async function AtlasHome() {
  const t = await getTranslations("Atlas");
  const home = await getTranslations("Home");
  const map = await getTranslations("Map");
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
      <section className={styles.discovery} aria-labelledby="discovery-title">
        <div className={styles.discoveryCopy}>
          <p className={styles.sectionEyebrow}>
            LIWA ATLAS / <bdi>AL REEM</bdi>
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
        <bdi>Liwa Atlas</bdi>
        <span>{t("pilot")}</span>
      </footer>
    </main>
  );
}
