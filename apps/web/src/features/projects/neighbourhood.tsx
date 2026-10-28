"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { Link } from "@/i18n/navigation";
import type { MapLabels, UseLabels } from "../atlas/types";
import { projectPositionQuality } from "./presentation";
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
  useLabels,
  truncatedLabel,
  googleUrl,
}: {
  territory: string;
  bounds: number[];
  slug: string;
  locations: ProjectMapLocation[];
  locale: string;
  labels: ProjectLabels;
  mapLabels: MapLabels;
  useLabels: UseLabels;
  truncatedLabel: string;
  googleUrl: string | null;
}) {
  const [active, setActive] = useState(false);
  const [local, setLocal] = useState(!googleUrl);
  const quality = projectPositionQuality(locations);
  return (
    <div className={styles.neighbourhood} data-neighbourhood={territory}>
      <p className={styles.mapIntro}>{labels.mapIntro}</p>
      {!locations.length && (
        <p className={styles.mapIntro} role="status">
          {labels.mapLocationPending}
        </p>
      )}
      {quality && <p className={styles.mapIntro}>{labels[quality.label]}</p>}
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
            useLabels={useLabels}
            truncatedLabel={truncatedLabel}
            unavailable={labels.mapUnavailable}
            loadingLabel={labels.loading}
            retryLabel={labels.retry}
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
