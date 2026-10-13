import {
  type ParcelProperty,
  preferredParcelProperty,
  propertyName,
  readableParcelCode,
  sourceLabel,
} from "./presentation";
import { PropertyCard } from "./property-card";
import type {
  AtlasLabels,
  MapContext,
  MapFeature,
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
}: {
  detail: ParcelDetail | null;
  feature: MapFeature | null;
  context: MapContext | null;
  labels: AtlasLabels;
  m: MapLabels;
  locale: string;
  select: (id: string) => void;
  parcelCodes: Record<string, string>;
  references: ResearchReference[];
  locate: () => void;
  choose: (feature: MapFeature) => void;
  parcelProperties: Map<string, ParcelProperty[]>;
}) {
  const date = (value: string | null | undefined) =>
    value
      ? new Intl.DateTimeFormat(locale, {
          dateStyle: "medium",
          timeStyle: value.length > 10 ? "short" : undefined,
          timeZone: "Asia/Dubai",
        }).format(new Date(value))
      : labels.unknown;
  const source = feature?.properties.source ?? detail?.source;
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
        ? m.parcelTitle
        : labels.select;
  return (
    <>
      {presented && presented.geometry.type !== "MultiLineString" ? (
        <PropertyCard
          key={presented.id}
          feature={presented}
          references={references}
          m={m}
          locale={locale}
          locate={locate}
          parcel={
            detail ? { code: detail.code, label: labels.reference } : undefined
          }
        />
      ) : (
        <div className="property-card">
          <h2>
            <bdi>{title || labels.select}</bdi>
          </h2>
          {preferred && (
            <span className="evidence-chip association-chip" title={m.spatial}>
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
          {feature.geometry.type === "Point" && (
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
          {!presented && (
            <button type="button" onClick={locate}>
              {m.locate}
            </button>
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
            <>
              <h3>{m.relatedProperties}</h3>
              <p className="small-text">{m.spatial}</p>
              {otherPlaces.map((place) => {
                const original = context?.place.features.find(
                  (f) => f.id === place.id,
                );
                return (
                  <p key={place.id}>
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
                );
              })}
            </>
          )}
          {!!detail.streets.length && (
            <>
              <h3>{m.nearby}</h3>
              <p className="small-text">{m.spatial}</p>
              {detail.streets.map((street) => (
                <p key={street.id}>
                  <bdi>{street.name}</bdi> · ≈{" "}
                  {new Intl.NumberFormat(locale).format(street.distance_m)} m
                </p>
              ))}
            </>
          )}
        </>
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
        </details>
      )}
    </>
  );
}
