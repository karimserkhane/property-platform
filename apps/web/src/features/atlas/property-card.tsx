import { useTranslations } from "next-intl";
import { useState } from "react";
import { ProjectMapSummary } from "@/features/projects/map-summary";
import { propertyName, readableParcelCode, sourceLabel } from "./presentation";
import type { MapFeature, MapLabels, ResearchReference } from "./types";

export function PropertyCard({
  feature,
  references,
  m,
  locale,
  locate,
  parcel,
}: {
  feature: MapFeature;
  references: ResearchReference[];
  m: MapLabels;
  locale: string;
  locate: () => void;
  parcel?: { code: string; label: string };
}) {
  const usageText = useTranslations("Use");
  const p = feature.properties;
  const profile = p.presentation;
  const isProject = p.kind.endsWith("_project_marker");
  const originalType =
    !isProject && !["yes", "no", ""].includes(p.kind) ? p.kind : "";
  const typeLabel = isProject
    ? m.project
    : p.use_types?.length
      ? usageText(p.use_types[0])
      : feature.geometry.type === "Point"
        ? m.places
        : m.building;
  const links = references.filter(
    (item) => item.place_id === feature.id && item.available,
  );
  const [failedImage, setFailedImage] = useState<string | null>(null);
  const [failedDelivery, setFailedDelivery] = useState<string | null>(null);
  const photo = profile?.media[0];
  const website =
    profile?.website_url ??
    links.find((link) => link.source_kind === "developer")?.url;
  const title = propertyName(p, locale) || typeLabel;
  if (profile?.project)
    return (
      <div className="property-card">
        <ProjectMapSummary
          key={profile.project.slug}
          slug={profile.project.slug}
          name={profile.project.name}
          developer={profile.developer}
          locale={locale}
          locate={locate}
          locateLabel={m.locate}
        />
        {parcel && (
          <p className="parcel-reference">
            <span>
              {parcel.label} · {m.possibleAssociation}
            </span>
            <bdi>{readableParcelCode(parcel.code)}</bdi>
          </p>
        )}
      </div>
    );
  return (
    <div className="property-card">
      <p className="property-kicker">{typeLabel}</p>
      <h2>
        <bdi>{title}</bdi>
      </h2>
      {(!!p.use_types?.length || originalType) && (
        <div className="property-use">
          <span>{usageText("sourceType")}</span>
          <strong>
            {p.use_types?.length ? (
              p.use_types.map((type) => usageText(type)).join(" · ")
            ) : (
              <bdi>{originalType}</bdi>
            )}
          </strong>
          {originalType && !!p.use_types?.length && (
            <small>
              {usageText("original")} : <bdi>{originalType}</bdi>
            </small>
          )}
          <a href={p.source.url} target="_blank" rel="noopener noreferrer">
            {sourceLabel(p.source.reliability, m)} ↗
          </a>
        </div>
      )}
      {(parcel || isProject) && (
        <span className="evidence-chip association-chip" title={m.spatial}>
          {parcel ? m.possibleAssociation : m.unverified}
        </span>
      )}
      {parcel && (
        <p className="parcel-reference">
          <span>{parcel.label}</span>
          <bdi>{readableParcelCode(parcel.code)}</bdi>
        </p>
      )}
      {profile && (
        <dl className="property-facts">
          {profile?.developer && (
            <>
              <dt>{m.developer}</dt>
              <dd>
                <bdi>{profile.developer}</bdi>
              </dd>
            </>
          )}
          {profile?.publisher && !profile.developer && (
            <>
              <dt>{m.providedBy}</dt>
              <dd>
                <bdi>{profile.publisher}</bdi>
              </dd>
            </>
          )}
        </dl>
      )}
      <div className="property-actions">
        {website && (
          <a
            className="property-website"
            href={website}
            target="_blank"
            rel="noopener noreferrer"
          >
            {website.split("?")[0].toLowerCase().endsWith(".pdf")
              ? m.propertyInformation
              : m.visitWebsite}{" "}
            ↗
          </a>
        )}
        <button type="button" onClick={locate}>
          {m.locate}
        </button>
      </div>
      {photo && (
        <figure className="property-photo">
          {failedImage === photo.id ? (
            <p role="status">{m.mediaUnavailable}</p>
          ) : (
            // biome-ignore lint/performance/noImgElement: bounded JPEG is already resized during acquisition; retain the guarded local media endpoint without a separate optimizer cache.
            <img
              src={
                photo.delivery_url && failedDelivery !== photo.id
                  ? photo.delivery_url
                  : `/api/atlas/property-media/${photo.id}`
              }
              alt={photo.caption}
              lang={photo.language}
              loading="lazy"
              decoding="async"
              onError={() => {
                if (photo.delivery_url && failedDelivery !== photo.id) {
                  setFailedDelivery(photo.id);
                } else {
                  setFailedImage(photo.id);
                }
              }}
            />
          )}
          <figcaption>
            <span lang={photo.language} dir="auto">
              {photo.caption}
            </span>
            <span>
              <a
                href={photo.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <bdi>{photo.author}</bdi>
              </a>
              {" · "}
              <a
                href={photo.licence_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {photo.licence_code}
              </a>
              {photo.taken_on && (
                <>
                  {" "}
                  ·{" "}
                  {new Intl.DateTimeFormat(locale, {
                    dateStyle: "medium",
                    timeZone: "UTC",
                  }).format(new Date(photo.taken_on))}
                </>
              )}
            </span>
          </figcaption>
        </figure>
      )}
      {profile?.summary && (
        <p className="property-description" lang={profile.language} dir="auto">
          {profile.summary}
        </p>
      )}
      {(p.levels != null || p.height_m != null) && (
        <dl className="property-facts">
          {p.levels != null && (
            <>
              <dt>{m.levels}</dt>
              <dd>{new Intl.NumberFormat(locale).format(p.levels)}</dd>
            </>
          )}
          {p.height_m != null && (
            <>
              <dt>{m.height}</dt>
              <dd>{new Intl.NumberFormat(locale).format(p.height_m)} m</dd>
            </>
          )}
        </dl>
      )}
      {(p.levels != null || p.height_m != null) && (
        <p className="small-text">
          <a href={p.source.url} target="_blank" rel="noopener noreferrer">
            {sourceLabel(p.source.reliability, m)} ↗
          </a>
        </p>
      )}
      {links
        .filter((link) => link.url !== website)
        .map((link) => (
          <a
            className="property-reference"
            href={link.url}
            key={link.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <bdi>{link.label}</bdi> ↗
          </a>
        ))}
      {profile && (
        <details className="property-proof">
          <summary>{m.propertyInformation}</summary>
          <p>
            <bdi>{profile.publisher}</bdi> ·{" "}
            {new Intl.DateTimeFormat(locale, {
              dateStyle: "medium",
              timeZone: "Asia/Dubai",
            }).format(new Date(profile.retrieved_at))}
          </p>
          <a
            href={profile.source_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {m.reference} ↗
          </a>
        </details>
      )}
    </div>
  );
}
