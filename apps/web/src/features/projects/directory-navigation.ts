export const PROJECT_DIRECTORY_PAGE_SIZE = 48;

type DirectoryNavigation = {
  territory?: string;
  query?: string;
  offset?: number;
};

/** Search and area changes share the same URL shape and reset pagination. */
export function projectDirectoryHref({
  territory,
  query,
  offset = 0,
}: DirectoryNavigation = {}) {
  return {
    pathname: "/projects",
    query: {
      ...(territory ? { territory } : {}),
      ...(query ? { q: query } : {}),
      ...(offset > 0 ? { offset } : {}),
    },
  };
}

/** A saved page remains usable if the source catalogue has fewer results. */
export function availableDirectoryOffset(offset: number, total: number) {
  const lastPage =
    Math.max(0, Math.ceil(total / PROJECT_DIRECTORY_PAGE_SIZE) - 1) *
    PROJECT_DIRECTORY_PAGE_SIZE;
  return Math.min(offset, lastPage);
}
