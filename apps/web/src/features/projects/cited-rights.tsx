import { useTranslations } from "next-intl";
import { SourceRights } from "./evidence";
import {
  type SourceRights as Rights,
  SOURCE_RIGHTS_LABELS,
  type SourceRightsLabels,
} from "./types";

/** The rights texts out of the Project labels or messages, for client components. */
export function pickRightsLabels(
  project: Record<string, unknown>,
): SourceRightsLabels {
  return Object.fromEntries(
    SOURCE_RIGHTS_LABELS.map((key) => [key, String(project[key] ?? "")]),
  ) as SourceRightsLabels;
}

/** Reviewed rights under a source cited outside a project dossier (A24). */
export function CitedRights({ rights }: { rights: Rights | null | undefined }) {
  const t = useTranslations("Project");
  if (!rights) return null;
  const labels = Object.fromEntries(
    SOURCE_RIGHTS_LABELS.map((key) => [key, t(key)]),
  ) as SourceRightsLabels;
  return <SourceRights source={{ rights }} labels={labels} />;
}
