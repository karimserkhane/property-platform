import type { ReactNode } from "react";
import { mapCreditText, mapCreditUrl } from "../atlas/map-credits";
import {
  type ActivityLabels,
  type ActivityParcel,
  activityBasisKey,
  activityState,
  describedParcels,
  formatHectares,
  type ProjectActivity,
} from "./activity";
import dossier from "./dossier.module.css";
import { formatProjectDate, safeSourceUrl } from "./presentation";
import styles from "./project.module.css";

type Shared = { locale: string; labels: ActivityLabels };

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function Day({ value, locale }: { value: string; locale: string }) {
  return (
    <time dateTime={value}>{formatProjectDate(value, locale) ?? value}</time>
  );
}

function Window({
  label,
  sceneId,
  window,
}: {
  label: string;
  sceneId: string;
  window: { url: string; content_sha256: string };
}) {
  const url = safeSourceUrl(window.url);
  return (
    <li>
      {label} · <bdi dir="ltr">{sceneId}</bdi>
      {url && (
        <>
          {" · "}
          <a href={url} target="_blank" rel="noopener noreferrer">
            <bdi dir="ltr">{window.content_sha256.slice(0, 12)}</bdi>{" "}
            <span aria-hidden="true">↗</span>
          </a>
        </>
      )}
    </li>
  );
}

function Parcel({
  parcel,
  locale,
  labels,
}: Shared & { parcel: ActivityParcel }) {
  const state = activityState(parcel);
  const basis = activityBasisKey(parcel);
  if (!state || !basis) return null;
  const number = new Intl.NumberFormat(locale);
  const plot = parcel.official_plot_id ?? parcel.source_record_id;
  return (
    <li
      className={`${styles.highlight} ${dossier.verification}`}
      data-activity-parcel={state.kind}
    >
      <h3>
        {labels.parcel} <bdi dir="ltr">{plot}</bdi>
      </h3>
      <dl className={dossier.verificationFacts}>
        <Fact label={labels.signal}>
          {state.kind === "measured" ? (
            <strong data-activity-level={state.latest.level}>
              {labels[state.level]}
            </strong>
          ) : (
            labels.insufficient
          )}
        </Fact>
        <Fact label={labels.beforeImage}>
          <Day value={state.latest.before_acquired_at} locale={locale} />
        </Fact>
        <Fact label={labels.afterImage}>
          <Day value={state.latest.after_acquired_at} locale={locale} />
        </Fact>
        <Fact label={labels.clearPixels}>
          {number.format(state.latest.clear_pixels)} {labels.clearOf}{" "}
          {number.format(state.latest.parcel_pixels)}
        </Fact>
        <Fact label={labels.basis}>{labels[basis]}</Fact>
        <Fact label={labels.area}>
          {formatHectares(parcel.area_m2, locale)} {labels.hectares}
        </Fact>
      </dl>
      {parcel.area_basis === "parcel_containing_position" && (
        <p className={styles.muted}>{labels.derivedNote}</p>
      )}
      <details className={`${styles.proof} ${dossier.proof}`}>
        <summary>{labels.images}</summary>
        <ul>
          <Window
            label={labels.beforeImage}
            sceneId={state.latest.before_scene_id}
            window={state.latest.before_window}
          />
          <Window
            label={labels.afterImage}
            sceneId={state.latest.after_scene_id}
            window={state.latest.after_window}
          />
        </ul>
        <p>
          {labels.methodVersion} ·{" "}
          <bdi dir="ltr">{state.latest.method_version}</bdi>
          {" · "}
          {labels.measuredOn}{" "}
          <Day value={state.latest.measured_at} locale={locale} />
        </p>
      </details>
    </li>
  );
}

/** Dated ground change seen on the project's parcels; a signal, never progress. */
export function ProjectActivitySection({
  activity,
  ...shared
}: Shared & { activity: ProjectActivity }) {
  const { labels } = shared;
  const parcels = describedParcels(activity);
  const source = safeSourceUrl(activity.source.url);
  return (
    <section
      className={styles.section}
      aria-labelledby="project-activity"
      data-project-activity={parcels.length ? "parcels" : "none"}
    >
      <div className={styles.sectionHeading}>
        <h2 id="project-activity">{labels.title}</h2>
      </div>
      <p className={styles.muted}>{labels.intro}</p>
      {parcels.length ? (
        <ul className={dossier.activityParcels}>
          {parcels.map((parcel) => (
            <Parcel
              key={`${parcel.source_namespace}:${parcel.source_record_id}`}
              parcel={parcel}
              {...shared}
            />
          ))}
        </ul>
      ) : (
        <p>{labels.noParcel}</p>
      )}
      <details className={`${styles.proof} ${dossier.proof}`}>
        <summary>{labels.method}</summary>
        <p>{labels.methodText}</p>
        <ul>
          <li>{labels.limitResolution}</li>
          <li>{labels.limitProgress}</li>
          <li>{labels.limitConditions}</li>
          <li>{labels.limitFrequency}</li>
        </ul>
        <p>
          {labels.source} ·{" "}
          {source ? (
            <a href={source} target="_blank" rel="noopener noreferrer">
              <bdi lang="en">{activity.source.name}</bdi>{" "}
              <span aria-hidden="true">↗</span>
            </a>
          ) : (
            <bdi lang="en">{activity.source.name}</bdi>
          )}
        </p>
        <p>
          {/* The reader's language; the registry keeps the original credit and its terms. */}
          <a
            href={mapCreditUrl("copernicus-sentinel") ?? undefined}
            target="_blank"
            rel="noopener noreferrer"
            title={mapCreditText("copernicus-sentinel")}
          >
            {labels.attribution}
          </a>
        </p>
      </details>
    </section>
  );
}
