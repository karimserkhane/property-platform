"use client";

import { useEffect, useId, useRef } from "react";
import { UiIcon } from "@/components/ui-icon";
import type { BuildingView } from "./building-3d";
import { BASEMAP_IMAGERY } from "./imagery-sources";
import styles from "./map-view-control.module.css";
import type { MapLabels } from "./types";

export function MapViewControl({
  satellite,
  scene,
  m,
  sourceLabel,
  locale,
  onChange,
  buildingView,
  onBuildingViewChange,
  commerce = false,
  onCommerceChange,
}: {
  satellite: boolean;
  scene: string;
  m: MapLabels;
  sourceLabel: string;
  locale: string;
  onChange: (satellite: boolean, scene: string) => void;
  buildingView: BuildingView;
  onBuildingViewChange: (view: BuildingView) => void;
  commerce?: boolean;
  onCommerceChange?: (value: boolean) => void;
}) {
  const radioId = useId();
  const root = useRef<HTMLDetailsElement>(null);
  const summary = useRef<HTMLElement>(null);
  useEffect(() => {
    const outside = (event: PointerEvent) => {
      if (
        root.current?.open &&
        event.target instanceof Node &&
        !root.current.contains(event.target)
      )
        root.current.open = false;
    };
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === "Escape" && root.current?.open) {
        event.stopPropagation();
        root.current.open = false;
        summary.current?.focus();
      }
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", dismiss);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", dismiss);
    };
  }, []);
  const provider = BASEMAP_IMAGERY.find((item) => item.id === scene);
  return (
    <details className={styles.root} ref={root} name="explore-map-controls">
      <summary ref={summary} aria-label={m.view}>
        <UiIcon name={satellite ? "layers" : "map"} />
        <span>{m.view}</span>
        {buildingView.dimension === "3d" && (
          <span className={styles.badge}>3D</span>
        )}
        <span className={styles.chevron} aria-hidden="true">
          ⌃
        </span>
      </summary>
      <div className={styles.panel}>
        {onCommerceChange && (
          <label className={styles.estimates}>
            <input
              type="checkbox"
              checked={commerce}
              onChange={(event) => onCommerceChange(event.target.checked)}
            />
            {m.commerce}
          </label>
        )}
        <fieldset className={styles.choices}>
          <legend className={styles.srOnly}>{m.view}</legend>
          {[false, true].map((value) => (
            <label
              key={String(value)}
              className={styles.choice}
              data-selected={satellite === value}
            >
              <input
                type="radio"
                name={`${radioId}-basemap`}
                checked={satellite === value}
                onChange={() => onChange(value, scene)}
              />
              <span
                className={value ? styles.satellite : styles.plan}
                aria-hidden="true"
              >
                <UiIcon name={value ? "layers" : "map"} />
              </span>
              <span>{value ? m.satellite : m.plan}</span>
            </label>
          ))}
        </fieldset>
        <fieldset className={styles.dimension}>
          <legend>{m.perspective}</legend>
          {(["2d", "3d"] as const).map((dimension) => (
            <label
              key={dimension}
              data-selected={buildingView.dimension === dimension}
            >
              <input
                type="radio"
                name={`${radioId}-dimension`}
                checked={buildingView.dimension === dimension}
                onChange={() =>
                  onBuildingViewChange({ ...buildingView, dimension })
                }
              />
              {dimension === "2d" ? m.flatView : m.buildings3d}
            </label>
          ))}
        </fieldset>
        {buildingView.dimension === "3d" && (
          <>
            <label className={styles.source}>
              <span>{m.buildingSource}</span>
              <select
                value={buildingView.buildingSource}
                onChange={(event) =>
                  onBuildingViewChange({
                    ...buildingView,
                    buildingSource:
                      event.target.value === "catalogue"
                        ? "catalogue"
                        : "openstreetmap",
                  })
                }
              >
                <option value="openstreetmap">{m.worldBuildings}</option>
                <option value="catalogue">{m.catalogueBuildings}</option>
              </select>
            </label>
            {buildingView.buildingSource === "catalogue" && (
              <label className={styles.estimates}>
                <input
                  type="checkbox"
                  checked={buildingView.estimatedHeights}
                  onChange={(event) =>
                    onBuildingViewChange({
                      ...buildingView,
                      estimatedHeights: event.target.checked,
                    })
                  }
                />
                {m.showEstimatedHeights}
              </label>
            )}
            <p className={styles.note}>
              {buildingView.buildingSource === "catalogue"
                ? m.catalogue3dNote
                : m.world3dNote}
            </p>
            <p className={styles.note}>{m.gesture3d}</p>
          </>
        )}
        {satellite && (
          <>
            <label className={styles.source}>
              <span>{m.imagerySource}</span>
              <select
                value={scene}
                onChange={(event) => onChange(true, event.target.value)}
              >
                {BASEMAP_IMAGERY.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.title}
                  </option>
                ))}
              </select>
            </label>
            {provider?.year && (
              <p className={styles.coverage}>{m.imageryCoverage}</p>
            )}
            <p className={styles.note}>{m.imageryNote}</p>
            {provider && (
              <a
                className={styles.evidence}
                href={provider.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                {sourceLabel} ↗
                {provider.year && (
                  <>
                    {" "}
                    · {m.imageryPeriod} :{" "}
                    {new Intl.NumberFormat(locale, {
                      useGrouping: false,
                    }).format(provider.year)}
                  </>
                )}
              </a>
            )}
          </>
        )}
      </div>
    </details>
  );
}
