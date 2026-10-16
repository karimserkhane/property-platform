"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { Link } from "@/i18n/navigation";
import type { MapLabels } from "../atlas/types";
import styles from "./project.module.css";
import type { ProjectLabels, ProjectMapLocation } from "./types";

const LocalMap = dynamic(() => import("./neighbourhood-map"), { ssr: false });

export function ProjectNeighbourhood({
  territory,
  bounds,
  slug,
  locations,
  locale,
  labels,
  mapLabels,
  googleUrl,
}: {
  territory: string;
  bounds: number[];
  slug: string;
  locations: ProjectMapLocation[];
  locale: string;
  labels: ProjectLabels;
  mapLabels: MapLabels;
  googleUrl: string | null;
}) {
  const [active, setActive] = useState(false);
  const [local, setLocal] = useState(!googleUrl);
  return (
    <div className={styles.neighbourhood} data-neighbourhood={territory}>
      <p className={styles.mapIntro}>{labels.mapIntro}</p>
      {active && !locations.length && (
        <p className={styles.mapIntro} role="status">
          {labels.mapLocationPending}
        </p>
      )}
      <div className={styles.neighbourhoodCanvas}>
        {!active ? (
          <div className={styles.mapInvitation}>
            <span className={styles.mapRose} aria-hidden="true">
              ⌖
            </span>
            <button
              className={styles.primaryAction}
              type="button"
              onClick={() => setActive(true)}
            >
              {labels.loadMap} <span aria-hidden="true">↗</span>
            </button>
          </div>
        ) : !local && googleUrl ? (
          <iframe
            title={labels.areaMap}
            src={googleUrl}
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            allowFullScreen
          />
        ) : (
          <LocalMap
            territory={territory}
            bounds={bounds}
            locations={locations}
            locale={locale}
            label={labels.areaMap}
            mapLabels={mapLabels}
            unavailable={labels.mapUnavailable}
          />
        )}
      </div>
      <div className={styles.mapFooter}>
        <Link
          href={{ pathname: "/explore", query: { territory, project: slug } }}
        >
          {labels.exploreArea} <span aria-hidden="true">↗</span>
        </Link>
        {googleUrl && !local && (
          <button
            type="button"
            onClick={() => {
              setLocal(true);
              setActive(true);
            }}
          >
            {labels.useLocalMap}
          </button>
        )}
      </div>
    </div>
  );
}
