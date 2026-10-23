import { useTranslations } from "next-intl";
import { type ReactNode, useState } from "react";
import { MapLocateButton } from "@/components/map-locate-button";
import { ProjectCover } from "@/features/projects/cover";
import { ProjectMapSummary } from "@/features/projects/map-summary";
import {
  type ParcelProperty,
  preferredParcelProperty,
  propertyName,
  readableParcelCode,
} from "./presentation";
import type { AtlasLabels, MapFeature, MapLabels, ParcelDetail } from "./types";

// A spatial candidate is an indication, never an implicit project identity.
export function SelectionPreview({
  detail,
  feature,
  labels,
  m,
  locale,
  parcelProperties,
  locate,
  children,
}: {
  detail: ParcelDetail | null;
  feature: MapFeature | null;
  labels: AtlasLabels;
  m: MapLabels;
  locale: string;
  parcelProperties: Map<string, ParcelProperty[]>;
  locate: () => void;
  children: ReactNode;
}) {
  const usage = useTranslations("Use");
  const projectLabels = useTranslations("Project");
  const [expanded, setExpanded] = useState(false);
  const candidates = detail ? [...(parcelProperties.get(detail.id) ?? [])] : [];
  for (const place of detail?.places ?? [])
    if (!candidates.some((candidate) => candidate.id === place.id))
      candidates.push({ ...place, feature: null });
  const candidate = preferredParcelProperty(candidates, locale);
  const identity = feature?.properties ?? candidate;
  const project = identity?.presentation?.project;
  const profile = identity?.presentation;
  const use =
    feature?.properties.use_types?.[0] ??
    (!candidate && detail?.use_types?.[0]);
  const kind = ["district", "community", "sector"].includes(
    identity?.kind ?? "",
  )
    ? m.areas
    : identity?.kind.endsWith("_project_marker")
      ? m.project
      : use
        ? usage(use)
        : feature?.geometry.type === "MultiLineString"
          ? m.streets
          : feature?.geometry.type === "Point"
            ? m.places
            : m.building;
  const title = identity && propertyName(identity, locale);
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  return (
    <>
      {project ? (
        <ProjectMapSummary
          slug={project.slug}
          name={project.name}
          developer={profile?.developer}
          locale={locale}
          locate={locate}
          locateLabel={m.locate}
        />
      ) : (
        <>
          {identity?.kind.endsWith("_project_marker") && (
            <ProjectCover
              compact
              labels={{
                visuals: projectLabels("visuals"),
                officialGallery: projectLabels("officialGallery"),
                source: projectLabels("source"),
                editorialImage: projectLabels("editorialImage"),
                previousImage: projectLabels("previousImage"),
                nextImage: projectLabels("nextImage"),
              }}
            />
          )}
          <article className="selection-preview">
            <p className="property-kicker">{detail ? m.parcels : kind}</p>
            <h2>
              <bdi>
                {title ||
                  (use ? usage(use) : detail?.land_use) ||
                  (detail ? m.parcelTitle : kind)}
              </bdi>
            </h2>
            {profile?.developer && (
              <p className="preview-developer">
                <bdi>{profile.developer}</bdi>
              </p>
            )}
            <dl className="preview-facts">
              {detail && (
                <div>
                  <dt>{m.area}</dt>
                  <dd>{number.format(detail.area_m2)} m²</dd>
                </div>
              )}
              {feature?.properties.levels != null && (
                <div>
                  <dt>{m.levels}</dt>
                  <dd>{number.format(feature.properties.levels)}</dd>
                </div>
              )}
              {feature?.properties.height_m != null && (
                <div>
                  <dt>{m.height}</dt>
                  <dd>{number.format(feature.properties.height_m)} m</dd>
                </div>
              )}
            </dl>
            <MapLocateButton label={m.locate} onClick={locate} />
          </article>
        </>
      )}
      {detail && (
        <p className="preview-reference">
          <span>{labels.reference}</span>
          <bdi>{readableParcelCode(detail.code)}</bdi>
          {candidate && <small>{m.possibleAssociation}</small>}
        </p>
      )}
      <details
        className="preview-details"
        onToggle={(event) => setExpanded(event.currentTarget.open)}
      >
        <summary>{m.propertyInformation}</summary>
        {expanded && candidate?.spatial_match && (
          <p className="proximity-note">
            {m.proximityMatch} · ≈{" "}
            {number.format(candidate.spatial_match.distance_m)} m{" "}
            <a
              href={candidate.feature?.properties.source.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {labels.source} ↗
            </a>
          </p>
        )}
        {expanded && children}
      </details>
    </>
  );
}
