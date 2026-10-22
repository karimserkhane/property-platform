import type { ReactNode } from "react";
import { UiIcon } from "@/components/ui-icon";
import { BUILDING_3D_COLORS, type BuildingView } from "./building-3d";
import { PLAN_COLORS } from "./hydrography";
import styles from "./map-legend.module.css";
import {
  MAP_MARKERS,
  type MapMarkerCategory,
  presentMarkerCategories,
} from "./map-markers";
import { type Category, COLORS } from "./presentation";
import type { MapContext, MapLabels } from "./types";

function MarkerSymbol({ category }: { category: MapMarkerCategory }) {
  const marker = MAP_MARKERS[category];
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.marker}>
      <path
        d={marker.frame}
        fill={marker.color}
        stroke="white"
        strokeWidth="1.5"
      />
      {marker.paths.map((path) => (
        <path
          key={path}
          d={path}
          fill="none"
          stroke="white"
          strokeWidth={category === "health" ? 3 : 1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}
    </svg>
  );
}

function Surface({
  color,
  children,
  outline = false,
}: {
  color: string;
  children: ReactNode;
  outline?: boolean;
}) {
  return (
    <span className={styles.item}>
      <i
        className={outline ? styles.outline : styles.swatch}
        style={{
          backgroundColor: outline ? "transparent" : color,
          borderColor: color,
        }}
      />
      {children}
    </span>
  );
}

/** The same symbols and taxonomy serve Explore and project neighbourhood maps. */
export function MapLegend({
  m,
  context,
  options,
  className,
  use = "",
  onUseChange,
}: {
  m: MapLabels;
  context: MapContext | null;
  options: BuildingView & {
    satellite: boolean;
    parcels?: boolean;
    places?: boolean;
    commerce?: boolean;
    buildings?: boolean;
  };
  className?: string;
  use?: string;
  onUseChange?: (value: string) => void;
}) {
  const categories = presentMarkerCategories(context, options);
  const parcels = options.parcels !== false;
  return (
    <details
      className={`${styles.legend} ${className ?? ""}`}
      name="explore-map-controls"
      onKeyDown={(event) => {
        if (event.key !== "Escape" || !event.currentTarget.open) return;
        event.preventDefault();
        event.stopPropagation();
        event.currentTarget.open = false;
        event.currentTarget.querySelector("summary")?.focus();
      }}
    >
      <summary>
        <UiIcon name="layers" />
        {m.legendToggle}
        <UiIcon name="chevron" />
      </summary>
      <div className={styles.panel}>
        <section className={styles.symbols} aria-label={m.markerTypes}>
          <strong>{m.markerTypes}</strong>
          <ul className={styles.grid}>
            {categories.map((category) => (
              <li key={category}>
                <MarkerSymbol category={category} />
                <span>{m[MAP_MARKERS[category].label]}</span>
              </li>
            ))}
            {options.buildings !== false && (
              <li>
                <Surface color="#688783">{m.building}</Surface>
              </li>
            )}
            {!options.satellite && (
              <li>
                <Surface color={PLAN_COLORS.water}>{m.water}</Surface>
              </li>
            )}
          </ul>
          {!options.satellite && (
            <p className={styles.hint}>{m.coastlineNotice}</p>
          )}
          {categories.includes("project") && (
            <p className={styles.hint}>
              <span className={styles.cluster} aria-hidden="true">
                3
              </span>
              {m.projectCluster}
            </p>
          )}
        </section>
        {parcels && (
          <details className={styles.section} open={Boolean(use)}>
            <summary>
              {m.legend}
              {use && <span className={styles.activeDot} aria-hidden="true" />}
              <UiIcon name="chevron" />
            </summary>
            <div className={styles.grid}>
              {Object.entries(COLORS).map(([key, color]) =>
                onUseChange ? (
                  <button
                    key={key}
                    type="button"
                    aria-pressed={use === key}
                    onClick={() => onUseChange(use === key ? "" : key)}
                  >
                    <Surface color={color} outline={key === "overlay"}>
                      {m[key as Category]}
                    </Surface>
                    {use === key && <span aria-hidden="true">✓</span>}
                  </button>
                ) : (
                  <Surface key={key} color={color} outline={key === "overlay"}>
                    {m[key as Category]}
                  </Surface>
                ),
              )}
            </div>
            <p className={styles.hint}>≈ {m.possibleAssociation}</p>
          </details>
        )}
        {options.dimension === "3d" && options.buildings !== false && (
          <details className={styles.section}>
            <summary>
              {m.buildings3d}
              <UiIcon name="chevron" />
            </summary>
            <div className={styles.heights}>
              {options.buildingSource === "catalogue" && (
                <Surface color={BUILDING_3D_COLORS.recorded}>
                  {m.recordedHeight}
                </Surface>
              )}
              <Surface color={BUILDING_3D_COLORS.estimated}>
                {m.estimatedHeight}
              </Surface>
            </div>
          </details>
        )}
      </div>
    </details>
  );
}
