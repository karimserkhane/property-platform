import registry from "@property-platform/contracts/map-credits" with {
  type: "json",
};

/** Map layers credited from the reviewed source rights registry (A19, A20). */
export type MapCreditLayer = keyof typeof registry;

const entities: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

export function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (character) => entities[character]);
}

/** `ODbL-1.0` → `ODbL 1.0`; registry codes stay recognisable. */
export function licenceName(code: string) {
  return code.replaceAll("-", " ");
}

/** The page a credit links to: the site's terms, else its licence. */
export function mapCreditUrl(layer: MapCreditLayer) {
  const credit = registry[layer];
  return credit.terms_url ?? credit.licence_url ?? null;
}

/** Plain credit of a layer (footers, PNG exports): attribution, detail, licence. */
export function mapCreditText(layer: MapCreditLayer, detail?: string) {
  const credit = registry[layer];
  return [credit.attribution, detail, licenceName(credit.licence)]
    .filter(Boolean)
    .join(" · ");
}

/** MapLibre attribution HTML: the plain credit, linked to the site's terms. */
export function mapCreditHtml(layer: MapCreditLayer, detail?: string) {
  const text = escapeHtml(mapCreditText(layer, detail));
  const url = mapCreditUrl(layer);
  return url
    ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${text}</a>`
    : text;
}
