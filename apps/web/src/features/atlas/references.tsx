import { CitedRights } from "@/features/projects/cited-rights";
import type { AtlasLabels, MapLabels, ResearchReference } from "./types";

export function References({
  items,
  labels,
  m,
  locale,
  choose,
}: {
  items: ResearchReference[];
  labels: AtlasLabels;
  m: MapLabels;
  locale: string;
  choose: (id: string) => void;
}) {
  return (
    <section className="atlas-source-list">
      <p className="small-text">
        {m.unverified} · {m.spatial}
      </p>
      {items.map((item) => (
        <article key={item.url}>
          <h3>
            <bdi>{item.label}</bdi>
          </h3>
          {item.title && (
            <p className="small-text">
              <bdi>{item.title}</bdi>
            </p>
          )}
          <p>
            <span>
              {
                m[
                  item.source_kind as
                    | "developer"
                    | "authority"
                    | "broker"
                    | "forum"
                    | "media"
                    | "reference"
                ]
              }
            </span>{" "}
            · {item.available ? m.projectReference : labels.unavailable}
          </p>
          <a href={item.url} target="_blank" rel="noopener noreferrer">
            {labels.source} ↗
          </a>
          <CitedRights rights={item.rights} />
          <p>
            {labels.retrieved} ·{" "}
            {new Intl.DateTimeFormat(locale, {
              dateStyle: "medium",
              timeStyle: "short",
              timeZone: "Asia/Dubai",
            }).format(new Date(item.retrieved_at))}
          </p>
          {item.place_id && (
            <button
              type="button"
              onClick={() => choose(item.place_id as string)}
            >
              {m.coordinates} →
            </button>
          )}
        </article>
      ))}
    </section>
  );
}
