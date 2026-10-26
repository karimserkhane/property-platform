import type { ReactNode } from "react";
import dossier from "./dossier.module.css";
import {
  formatObservedRange,
  type ObservedSales,
  type ObservedSalesGroup,
  type ObservedSalesLabels,
  partialShareCount,
  saleApplicationKey,
  saleSequenceKey,
} from "./observed-sales";
import { formatProjectDate, safeSourceUrl } from "./presentation";
import styles from "./project.module.css";

type Shared = { locale: string; labels: ObservedSalesLabels };

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

/** A translated closed ADREC value, or the original text. */
function Kind({ value, label }: { value: string; label: string | null }) {
  return label ?? <bdi lang="en">{value}</bdi>;
}

function Group({
  group,
  locale,
  labels,
}: Shared & { group: ObservedSalesGroup }) {
  const number = new Intl.NumberFormat(locale);
  const money = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "AED",
    maximumFractionDigits: 0,
  });
  const decimal = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  const range = (
    value: ObservedSalesGroup["price_aed"],
    format: (value: number) => string,
  ) => {
    const text = value && formatObservedRange(value, format);
    return text ? <bdi>{text}</bdi> : labels.noRange;
  };
  const application = saleApplicationKey(group.sale_application_type);
  const sequence = saleSequenceKey(group.sale_sequence);
  const partial = partialShareCount(group);
  return (
    <li
      className={`${styles.highlight} ${dossier.verification}`}
      data-observed-sales-group
    >
      <h3>
        <bdi lang="en">{group.property_type}</bdi> ·{" "}
        <bdi lang="en">{group.property_layout}</bdi>
      </h3>
      <p className={styles.muted}>
        <Kind
          value={group.sale_application_type}
          label={application && labels[application]}
        />{" "}
        ·{" "}
        <Kind
          value={group.sale_sequence}
          label={sequence && labels[sequence]}
        />
      </p>
      <dl className={dossier.verificationFacts}>
        <Fact label={labels.sales}>
          <strong>{number.format(group.sales_count)}</strong>
        </Fact>
        <Fact label={labels.price}>
          {range(group.price_aed, (value) => money.format(value))}
        </Fact>
        <Fact label={labels.rate}>
          {range(
            group.rate_aed_per_sqm,
            (value) => `${money.format(value)} ${labels.perSquareMetre}`,
          )}
        </Fact>
        <Fact label={labels.area}>
          {range(group.sold_area_sqm, (value) => `${decimal.format(value)} m²`)}
        </Fact>
        <Fact label={labels.registered}>
          <Day value={group.first_registration_date} locale={locale} /> –{" "}
          <Day value={group.last_registration_date} locale={locale} />
        </Fact>
        {partial > 0 && (
          <Fact label={labels.partialShares}>{number.format(partial)}</Fact>
        )}
      </dl>
    </li>
  );
}

/** Recorded ADREC sales of the project, by type: ranges and counts, never a price. */
export function ProjectObservedSalesSection({
  sales,
  ...shared
}: Shared & { sales: ObservedSales }) {
  const { labels, locale } = shared;
  const source = safeSourceUrl(sales.source.url);
  const window = sales.window;
  return (
    <section
      className={styles.section}
      aria-labelledby="project-sales"
      data-project-sales={
        !window ? "no-window" : sales.groups.length ? "groups" : "none"
      }
    >
      <div className={styles.sectionHeading}>
        <h2 id="project-sales">{labels.title}</h2>
      </div>
      <p className={styles.muted}>{labels.intro}</p>
      {window ? (
        <p>
          {labels.window} · <Day value={window.period_start} locale={locale} />{" "}
          – <Day value={window.period_end} locale={locale} />
        </p>
      ) : (
        <p>{labels.noWindow}</p>
      )}
      {window && !sales.groups.length && <p>{labels.noSales}</p>}
      {sales.groups.length > 0 && (
        <ul className={dossier.salesGroups}>
          {sales.groups.map((group) => (
            <Group
              key={[
                group.property_type,
                group.property_layout,
                group.sale_application_type,
                group.sale_sequence,
              ].join("|")}
              group={group}
              {...shared}
            />
          ))}
        </ul>
      )}
      <p className={styles.muted}>{labels.askingPrice}</p>
      <details className={`${styles.proof} ${dossier.proof}`}>
        <summary>{labels.method}</summary>
        <p>{labels.methodText}</p>
        <ul>
          <li>{labels.limitWindow}</li>
          <li>{labels.limitPartial}</li>
          <li>{labels.limitNames}</li>
          <li>{labels.limitTypes}</li>
        </ul>
        <p>{labels.linkedNames}</p>
        <ul>
          {sales.labels.map((item) => (
            <li key={`${item.district}|${item.label}`}>
              <bdi lang="en">{item.label}</bdi> ·{" "}
              <bdi lang="en">{item.district}</bdi> ·{" "}
              {item.evidence === "register_name"
                ? labels.evidenceRegisterName
                : labels.evidenceProjectName}
              {item.registration_number && (
                <>
                  {" "}
                  (<bdi dir="ltr">{item.registration_number}</bdi>)
                </>
              )}{" "}
              · {labels.reviewedOn}{" "}
              <Day value={item.reviewed_on} locale={locale} />
            </li>
          ))}
        </ul>
        {window && (
          <>
            <p>
              {labels.collected}{" "}
              <Day value={window.collected_at} locale={locale} />
            </p>
            {window.captures.length > 0 && (
              <ul>
                {window.captures.map((capture) => {
                  const url = safeSourceUrl(capture.url);
                  const digest = (
                    <bdi dir="ltr">{capture.content_sha256.slice(0, 12)}</bdi>
                  );
                  return (
                    <li key={`${capture.url}|${capture.content_sha256}`}>
                      {labels.capture} ·{" "}
                      {url ? (
                        <a href={url} target="_blank" rel="noopener noreferrer">
                          {digest} <span aria-hidden="true">↗</span>
                        </a>
                      ) : (
                        digest
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </>
        )}
        <p>
          {labels.source} ·{" "}
          {source ? (
            <a href={source} target="_blank" rel="noopener noreferrer">
              <bdi lang="en">{sales.source.name}</bdi>{" "}
              <span aria-hidden="true">↗</span>
            </a>
          ) : (
            <bdi lang="en">{sales.source.name}</bdi>
          )}
        </p>
      </details>
    </section>
  );
}
