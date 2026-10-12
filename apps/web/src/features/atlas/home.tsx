import { brand } from "@property-platform/branding";
import navigation from "@property-platform/contracts/territories";
import { getLocale, getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import styles from "./home.module.css";
import { HomeExperience } from "./home-experience";
import { HomeGallery } from "./home-gallery";
import { type GalleryLabels, HOME_SCENES } from "./home-scenes";

export async function AtlasHome() {
  const t = await getTranslations("Atlas");
  const home = await getTranslations("Home");
  const map = await getTranslations("Map");
  const coverage = await getTranslations("Coverage");
  const locale = await getLocale();
  const coast = HOME_SCENES[1];
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
    <HomeExperience>
      <section
        className={styles.hero}
        data-scene="hero"
        aria-labelledby="home-title"
      >
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
        <a className={styles.scrollCue} href="#discovery">
          <span aria-hidden="true">↓</span>
          {home("scroll")}
        </a>
      </section>
      <section
        className={styles.discovery}
        id="discovery"
        data-scene="chapter"
        aria-labelledby="discovery-title"
      >
        <div className={styles.discoveryCopy} data-reveal="visible">
          <p className={styles.sectionEyebrow}>
            <span aria-hidden="true">01 /</span> <bdi>{brand.displayName}</bdi>
          </p>
          <h2 id="discovery-title">{home("discoverTitle")}</h2>
          <p>{home("discoverBody")}</p>
          <div className={styles.layerLinks}>
            {[
              map("parcels"),
              map("streets"),
              map("buildings"),
              t("sources"),
            ].map((label, index) => (
              <Link key={label} href="/explore" className={styles.layerLink}>
                <span className={styles.layerIndex} aria-hidden="true">
                  0{index + 1}
                </span>
                <span>{label}</span>
                <span className={styles.layerArrow} aria-hidden="true">
                  ↗
                </span>
              </Link>
            ))}
          </div>
        </div>
        <figure className={styles.discoveryVisual} data-reveal="visible">
          <div className={styles.discoveryFrame}>
            <picture className={styles.chapterMedia}>
              <source
                media="(max-width: 700px)"
                srcSet={`/images/uae/${coast.image}-768.webp`}
              />
              <img
                src={`/images/uae/${coast.image}-1920.webp`}
                alt=""
                width="1920"
                height={coast.height}
                loading="lazy"
                decoding="async"
              />
            </picture>
            <span className={styles.imageLabel}>{home("coast")}</span>
          </div>
          <figcaption>
            <span>{home("location")}</span>
            <a href={coast.url} target="_blank" rel="noopener noreferrer">
              {home("photoCredit")}: <bdi>{coast.photographer}</bdi> / Unsplash
              ↗
            </a>
          </figcaption>
        </figure>
      </section>
      <section className={styles.regions} aria-labelledby="regions-title">
        <div className={styles.regionIntro} data-reveal="visible">
          <p className={styles.sectionEyebrow}>
            <span aria-hidden="true">02 /</span> {home("location")}
          </p>
          <h2 id="regions-title">{coverage("title")}</h2>
          <p className={styles.regionNote}>{home("coverage")}</p>
        </div>
        <div className={styles.regionGrid}>
          {navigation.territories
            .filter((territory) => territory.level === "emirate")
            .map((territory, index) => {
              const pilot = navigation.territories.find(
                (area) => area.parent_id === territory.id && area.queryable,
              );
              return (
                <Link
                  key={territory.id}
                  className={`${styles.regionCard} ${pilot ? styles.pilotCard : ""}`}
                  data-reveal="visible"
                  href={{
                    pathname: "/explore",
                    query: { territory: pilot?.id ?? territory.id },
                  }}
                >
                  <span className={styles.regionIndex} aria-hidden="true">
                    0{index + 1}
                  </span>
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
    </HomeExperience>
  );
}
