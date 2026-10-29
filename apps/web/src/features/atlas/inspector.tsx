import { useTranslations } from "next-intl";
import { Fragment } from "react";
import { MapLocateButton } from "@/components/map-locate-button";
import { CitedRights } from "@/features/projects/cited-rights";
import {
  featureShape,
  listedRights,
  type ParcelProperty,
  preferredParcelProperty,
  propertyName,
  readableParcelCode,
  sourceLabel,
} from "./presentation";
import { PropertyCard } from "./property-card";
import { Surroundings } from "./surroundings";
import type {
  AtlasContext,
  AtlasFeature,
  AtlasLabels,
  MapLabels,
  ParcelDetail,
  ResearchReference,
} from "./types";

export function Inspector({
  detail,
  feature,
  context,
  labels,
  m,
  locale,
  select,
  parcelCodes,
  references,
  locate,
  choose,
  parcelProperties,
  territory,
  showIdentity = true,
}: {
  detail: ParcelDetail | null;
  feature: AtlasFeature | null;
  context: AtlasContext | null;
  labels: AtlasLabels;
  m: MapLabels;
  locale: string;
  select: (id: string) => void;
  parcelCodes: Record<string, string>;
  references: ResearchReference[];
  locate: () => void;
  choose: (feature: AtlasFeature) => void;
  parcelProperties: Map<string, ParcelProperty[]>;
  territory: string;
  showIdentity?: boolean;
}) {
  const usageText = useTranslations("Use");
  const date = (value: string | null | undefined) =>
    value
      ? new Intl.DateTimeFormat(locale, {
          dateStyle: "medium",
          timeStyle: value.length > 10 ? "short" : undefined,
          timeZone: "Asia/Dubai",
        }).format(new Date(value))
      : labels.unknown;
  const source = feature?.properties.source ?? detail?.source;
  const layers = Object.values(context ?? {});
  // A map feature's rights come once per site with its list; a parcel's with its detail.
  const sourceRights = feature
    ? listedRights(feature.properties.source.url, layers)
    : detail?.source.rights;
  const a = detail?.attributes;
  const candidates = detail ? [...(parcelProperties.get(detail.id) ?? [])] : [];
  for (const place of detail?.places ?? []) {
    if (!candidates.some((p) => p.id === place.id))
      candidates.push({ ...place, feature: null });
  }
  const preferred = preferredParcelProperty(candidates, locale);
  const presented = feature ?? preferred?.feature;
  const otherPlaces =
    detail?.places.filter((p) => p.id !== preferred?.id) ?? [];
  const title = feature
    ? propertyName(feature.properties, locale)
    : preferred
      ? propertyName(preferred, locale)
      : detail
        ? detail.use_types?.length
          ? usageText(detail.use_types[0])
          : detail.land_use || m.parcelTitle
        : labels.select;
  return (
    <>
      {Object.keys(
        detail?.field_history ?? feature?.properties.field_history ?? {},
      ).length > 0 && (
        <details className="small-text">
          <summary>{m.historical}</summary>
          {Object.entries(
            detail?.field_history ?? feature?.properties.field_history ?? {},
          ).map(([field, source]) => (
            <Fragment key={field}>
              <p>
                <bdi>{field}</bdi> · {date(source.retrieved_at)} ·{" "}
                <a href={source.url} target="_blank" rel="noopener noreferrer">
                  {labels.source} ↗
                </a>
              </p>
              <CitedRights rights={source.rights} />
            </Fragment>
          ))}
        </details>
      )}
      {(showIdentity || !presented?.properties.presentation?.project) &&
        (presented && featureShape(presented) !== "MultiLineString" ? (
          <PropertyCard
            key={`property-card:${presented.id}`}
            feature={presented}
            references={references}
            m={m}
            locale={locale}
            locate={locate}
            parcel={
              detail
                ? { code: detail.code, label: labels.reference }
                : undefined
            }
          />
        ) : (
          <div className="property-card">
            <h2>
              <bdi>{title || labels.select}</bdi>
            </h2>
            {preferred && (
              <span
                className="evidence-chip association-chip"
                title={m.spatial}
              >
                {m.possibleAssociation}
              </span>
            )}
            {detail && (
              <p className="parcel-reference">
                <span>{labels.reference}</span>
                <bdi>{readableParcelCode(detail.code)}</bdi>
              </p>
            )}
          </div>
        ))}
      {!!detail?.overlapping_parcels.length && (
        <div className="parcel-overlap">
          <p>{m.overlapAlert}</p>
          <details className="property-proof">
            <summary>{m.overlappingRecords}</summary>
            <p className="small-text">{m.overlapNote}</p>
            {detail.overlapping_parcels.map((parcel) => (
              <div className="overlap-record" key={parcel.id}>
                <button
                  type="button"
                  className="candidate-button"
                  onClick={() => select(parcel.id)}
                >
                  <strong>
                    {parcel.use_types[0]
                      ? usageText(parcel.use_types[0])
                      : parcel.land_use}
                  </strong>
                  <bdi>{readableParcelCode(parcel.code)}</bdi> →
                </button>
                <small>
                  <bdi>
                    {parcel.land_use} · {parcel.ownership}
                  </bdi>
                </small>
                <a
                  href={parcel.source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {labels.source} ↗
                </a>
                <CitedRights rights={parcel.source.rights} />
              </div>
            ))}
          </details>
        </div>
      )}
      {detail?.land_use && (
        <div className="property-use">
          <span>{usageText("publishedLandUse")}</span>
          {!!detail.use_types?.length && (
            <strong>
              {detail.use_types.map((type) => usageText(type)).join(" · ")}
            </strong>
          )}
          <small>
            {usageText("original")} : <bdi>{detail.land_use}</bdi>
          </small>
        </div>
      )}
      {feature && (
        <details className="property-proof">
          <summary>{m.mapDetails}</summary>
          <span className="evidence-chip">
            {sourceLabel(feature.properties.source.reliability, m)}
          </span>
          <p className="small-text">{m.spatial}</p>
          {feature.properties.parcel_ids.map((id) => (
            <button
              className="candidate-button"
              key={id}
              type="button"
              onClick={() => select(id)}
            >
              <bdi>{readableParcelCode(parcelCodes[id] ?? labels.unknown)}</bdi>{" "}
              →
            </button>
          ))}
          {"geometry" in feature && feature.geometry.type === "Point" && (
            <p>
              <span>{m.coordinates} </span>
              <bdi>
                {(feature.geometry.coordinates as number[])
                  .map((v) => v.toFixed(6))
                  .join(", ")}
              </bdi>
            </p>
          )}
        </details>
      )}
      {detail && (
        <>
          {showIdentity && !presented && (
            <MapLocateButton label={m.locate} onClick={locate} />
          )}
          <details className="property-proof">
            <summary>{m.parcelDetails}</summary>
            <span className="evidence-chip">{m.official}</span>
            {preferred && <p className="small-text">{m.spatial}</p>}
            <dl>
              <dt>{labels.reference}</dt>
              <dd>
                <bdi>{detail.code}</bdi>
              </dd>
              <dt>{m.landUse}</dt>
              <dd>
                <bdi>{detail.land_use || labels.unknown}</bdi>
              </dd>
              <dt>{m.area}</dt>
              <dd>{new Intl.NumberFormat(locale).format(detail.area_m2)}</dd>
              <dt>{m.construction}</dt>
              <dd>
                <bdi>{detail.construction_status || labels.unknown}</bdi>
              </dd>
              <dt>{labels.community}</dt>
              <dd>
                <bdi>{detail.community}</bdi>
              </dd>
              {a && (
                <>
                  <dt>{m.planning}</dt>
                  <dd>
                    <bdi>{a.planning || labels.unknown}</bdi>
                  </dd>
                  <dt>{m.ownership}</dt>
                  <dd>
                    <bdi>{a.ownership || labels.unknown}</bdi>
                  </dd>
                  <dt>{m.allocation}</dt>
                  <dd>
                    <bdi>{a.allocation || labels.unknown}</bdi>
                  </dd>
                  <dt>{m.approval}</dt>
                  <dd>{date(a.approval_date)}</dd>
                  <dt>{m.received}</dt>
                  <dd>{date(a.received_date)}</dd>
                  <dt>{m.permit}</dt>
                  <dd>
                    {date(a.permit_date)} <bdi>{a.permit_type}</bdi>
                  </dd>
                  <dt>{m.meps}</dt>
                  <dd>
                    <bdi>
                      {a.meps || labels.unknown} {a.meps_updated}
                    </bdi>
                  </dd>
                </>
              )}
            </dl>
            {a?.dcr_url && (
              <p>
                <a href={a.dcr_url} target="_blank" rel="noopener noreferrer">
                  {m.dcr} ↗
                </a>
              </p>
            )}
          </details>
          {!!otherPlaces.length && (
            <details className="property-proof">
              <summary>{m.relatedProperties}</summary>
              <p className="small-text">{m.spatial}</p>
              {otherPlaces.map((place) => {
                const original = context?.place.features.find(
                  (f) => f.id === place.id,
                );
                return (
                  <Fragment key={place.id}>
                    <p>
                      {original ? (
                        <button
                          type="button"
                          className="candidate-button"
                          onClick={() => choose(original)}
                        >
                          <bdi>
                            {(locale === "ar" && place.name_ar) ||
                              place.name ||
                              place.name_ar}
                          </bdi>{" "}
                          →
                        </button>
                      ) : (
                        <bdi>
                          {(locale === "ar" && place.name_ar) ||
                            place.name ||
                            place.name_ar}
                        </bdi>
                      )}
                      {original && (
                        <>
                          {" "}
                          ·{" "}
                          <a
                            href={original.properties.source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {labels.source} ↗
                          </a>
                        </>
                      )}
                    </p>
                    {original && (
                      <CitedRights
                        rights={listedRights(original.properties.source.url, [
                          context?.place,
                        ])}
                      />
                    )}
                  </Fragment>
                );
              })}
            </details>
          )}
          {!!detail.streets.length && (
            <details className="property-proof">
              <summary>{m.nearby}</summary>
              <p className="small-text">{m.spatial}</p>
              {detail.streets.map((street) => (
                <p key={street.id}>
                  <bdi>{street.name}</bdi> · ≈{" "}
                  {new Intl.NumberFormat(locale).format(street.distance_m)} m
                </p>
              ))}
            </details>
          )}
        </>
      )}
      {(detail || feature) &&
        !["district", "community", "sector"].includes(
          feature?.properties.kind ?? "",
        ) && (
          <Surroundings
            key={`surroundings:${territory}:${detail ? "parcel" : feature && featureShape(feature)}:${detail?.id ?? feature?.id}`}
            identity={(detail?.id ?? feature?.id) as string}
            target={
              detail
                ? "parcel"
                : (feature && featureShape(feature)) === "Point"
                  ? "place"
                  : (feature && featureShape(feature)) === "MultiPolygon"
                    ? "building"
                    : "street"
            }
            territory={territory}
            m={m}
            labels={labels}
            locale={locale}
          />
        )}
      {source && (
        <details className="source-detail">
          <summary>{m.sourceDate}</summary>
          <dl>
            <dt>{labels.retrieved}</dt>
            <dd>{date(source.retrieved_at)}</dd>
            <dt>
              {feature?.properties.source.reliability === "community"
                ? m.editedDate
                : labels.published}
            </dt>
            <dd>{date(source.published_at)}</dd>
          </dl>
          <a
            className="text-link"
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {labels.source} ↗
          </a>
          <p className="small-text">
            <bdi>{source.name}</bdi>
          </p>
          <CitedRights rights={sourceRights} />
        </details>
      )}
    </>
  );
}
