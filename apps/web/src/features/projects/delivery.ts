import type { components } from "@property-platform/contracts";

export type DeliveryHistory =
  components["schemas"]["DeveloperDeliveryHistoryResponse"];
export type DeliveryProject = DeliveryHistory["projects"][number];
export type DeliveryAnnouncement = DeliveryProject["announcements"][number];
export type DeliveryLabels = Record<
  keyof typeof import("../../../messages/en.json").Delivery,
  string
>;

type PreviewReader = (
  path: string,
) => Promise<{ status: number; data: unknown }>;

// Same rule as the API: a developer key is a reviewed slug, never a visitor URL.
export function isDeveloperKey(key: string) {
  return key.length <= 100 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(key);
}

export function developerHistoryHref(key: string) {
  return `/developers/${key}`;
}

export async function readDeliveryHistoryData(
  key: string,
  read: PreviewReader,
) {
  if (!isDeveloperKey(key)) return { status: 404, history: null };
  try {
    const result = await read(
      `developers/${encodeURIComponent(key)}/delivery-history`,
    );
    if (result.status !== 200) return { status: result.status, history: null };
    const history = result.data as DeliveryHistory | null;
    if (
      !history ||
      history.developer?.key !== key ||
      typeof history.developer.name !== "string" ||
      !history.summary ||
      !Array.isArray(history.projects) ||
      !history.projects.every(
        (project) =>
          typeof project.slug === "string" &&
          Array.isArray(project.announcements) &&
          Array.isArray(project.register_readings),
      )
    )
      return { status: 503, history: null };
    return { status: 200, history };
  } catch {
    return { status: 503, history: null };
  }
}

const changeKeys = {
  first: "changeFirst",
  later: "changeLater",
  earlier: "changeEarlier",
  refined: "changeRefined",
} as const;

const outcomeKeys = {
  met: "outcomeMet",
  late: "outcomeLate",
  undetermined: "outcomeUndetermined",
} as const;

export function deliveryChangeKey(change: string) {
  return Object.hasOwn(changeKeys, change)
    ? changeKeys[change as keyof typeof changeKeys]
    : null;
}

export function deliveryOutcomeKey(status: string) {
  return Object.hasOwn(outcomeKeys, status)
    ? outcomeKeys[status as keyof typeof outcomeKeys]
    : null;
}

/** Projects with dated observations first; the others are only listed. */
export function splitDeliveryProjects(projects: DeliveryProject[]) {
  const observed = projects.filter(
    (project) =>
      project.announcements.length > 0 || project.register_readings.length > 0,
  );
  const silent = projects.filter((project) => !observed.includes(project));
  return { observed, silent };
}
