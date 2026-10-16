import type { ProjectDetail } from "./types";

type PreviewReader = (
  path: string,
) => Promise<{ status: number; data: unknown }>;

// This testable adapter never accepts an origin or source URL from a visitor.
export function isProjectSlug(slug: string) {
  return slug.length <= 100 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug);
}

export function projectMapHref(slug: string, territory: string) {
  return { pathname: "/explore", query: { territory, project: slug } };
}

export async function readProjectData(slug: string, read: PreviewReader) {
  if (!isProjectSlug(slug)) return { status: 404, project: null };
  try {
    const result = await read(`projects/${encodeURIComponent(slug)}`);
    if (result.status !== 200) return { status: result.status, project: null };
    if (!result.data) return { status: 503, project: null };
    const project = result.data as ProjectDetail;
    if (
      project.slug !== slug ||
      typeof project.name !== "string" ||
      !project.developer ||
      typeof project.developer.name !== "string" ||
      !Array.isArray(project.sources) ||
      !Array.isArray(project.media) ||
      !Array.isArray(project.typologies) ||
      !Array.isArray(project.amenities)
    )
      return { status: 503, project: null };
    return { status: 200, project };
  } catch {
    return { status: 503, project: null };
  }
}
