import { brand } from "@property-platform/branding";
import navigation from "@property-platform/contracts/territories";
import { getLocale, getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import styles from "./home.module.css";
import { HomeExperience } from "./home-experience";
import { HOME_SCENES } from "./home-scenes";
import { HomeVisual } from "./home-visual";

export async function AtlasHome() {
  const t = await getTranslations("Atlas");
  const home = await getTranslations("Home");
  const map = await getTranslations("Map");
  const coverage = await getTranslations("Coverage");
  const project = await getTranslations("Project");
  const locale = await getLocale();
  const coast = HOME_SCENES[1];
  const sunset = HOME_SCENES[2];
  const areas = navigation.territories.filter(
    (territory) => territory.level === "area" && territory.queryable,
  );
  return (
    <HomeExperience>
      <section
        className={styles.hero}
        data-scene="hero"
        aria-labelledby="home-title"
      >
        <HomeVisual />
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
            <Link className={styles.secondaryAction} href="/projects">
              {project("projects")} <span aria-hidden="true">↗</span>
            </Link>
          </div>
          <p className={styles.coverage}>{home("coverage")}</p>
        </div>
        <a className={styles.scrollCue} href="#discovery">
          <span aria-hidden="true">↓</span>
          {home("scroll")}
        </a>
      </section>
      <section className={styles.start} aria-labelledby="start-title">
        <div className={styles.startHeading}>
          <p className={styles.sectionEyebrow}>{home("navExplore")}</p>
          <h2 id="start-title">{home("startTitle")}</h2>
          <p>{home("startDescription")}</p>
          <a className={styles.startMore} href="#regions">
            {coverage("chooseEmirate")} <span aria-hidden="true">↓</span>
          </a>
        </div>
        <div className={styles.areaLinks}>
          {areas.map((area) => (
            <Link
              key={area.id}
              className={styles.areaLink}
              href={{ pathname: "/explore", query: { territory: area.id } }}
            >
              <span className={styles.areaIcon} aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M19 10c0 5-7 10-7 10S5 15 5 10a7 7 0 0 1 14 0Z"
                    stroke="currentColor"
                    strokeWidth="1.4"
                  />
                  <circle
                    cx="12"
                    cy="10"
                    r="2.5"
                    stroke="currentColor"
                    strokeWidth="1.4"
                  />
                </svg>
              </span>
              <span className={styles.areaName}>
                <bdi>{locale === "ar" ? area.name_ar : area.name}</bdi>
                <span>{t("map")}</span>
              </span>
              <span className={styles.areaArrow} aria-hidden="true">
                ↗
              </span>
            </Link>
          ))}
          <Link className={styles.areaDirectory} href="/projects">
            {project("projects")} <span aria-hidden="true">↗</span>
          </Link>
        </div>
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
              { label: project("projects"), href: "/projects" },
              {
                label: map("buildings"),
                href: { pathname: "/explore", query: { tab: "buildings" } },
              },
              {
                label: map("places"),
                href: { pathname: "/explore", query: { tab: "places" } },
              },
              {
                label: map("streets"),
                href: { pathname: "/explore", query: { tab: "streets" } },
              },
            ].map(({ label, href }, index) => (
              <Link key={label} href={href} className={styles.layerLink}>
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
          </div>
          <figcaption>
            <span>{home("location")}</span>
          </figcaption>
        </figure>
      </section>
      <section
        id="regions"
        className={styles.regions}
        aria-labelledby="regions-title"
      >
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
                    query: { territory: territory.id },
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
      <section className={styles.invitation} aria-labelledby="invitation-title">
        <picture className={styles.invitationPhoto}>
          <source
            media="(max-width: 700px)"
            srcSet={`/images/uae/${sunset.image}-768.webp`}
          />
          <img
            src={`/images/uae/${sunset.image}-1920.webp`}
            alt=""
            width="1920"
            height={sunset.height}
            loading="lazy"
            decoding="async"
          />
        </picture>
        <div className={styles.invitationCopy} data-reveal="visible">
          <p className={styles.eyebrow}>{home("location")}</p>
          <h2 id="invitation-title">{home("invitationTitle")}</h2>
          <p>{home("invitationBody")}</p>
          <Link href="/explore" className={styles.primaryAction}>
            {t("explore")} <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </section>
      <footer className={styles.footer}>
        <bdi>{brand.displayName}</bdi>
        <span>{t("pilot")}</span>
      </footer>
    </HomeExperience>
  );
}
