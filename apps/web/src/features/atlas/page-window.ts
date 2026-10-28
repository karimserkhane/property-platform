export type PageWindowItem = number | "ellipsis-start" | "ellipsis-end";

/** A bounded, zero-based window that keeps the current page and both endpoints. */
export function pageWindow(page: number, pageCount: number) {
  const total = Number.isSafeInteger(pageCount) ? Math.max(0, pageCount) : 0;
  const current = Math.min(
    Math.max(0, Number.isSafeInteger(page) ? page : 0),
    Math.max(0, total - 1),
  );
  let pages: number[];
  if (total <= 5) {
    pages = Array.from({ length: total }, (_, index) => index);
  } else if (current <= 2) {
    pages = [0, 1, 2, 3, total - 1];
  } else if (current >= total - 3) {
    pages = [0, total - 4, total - 3, total - 2, total - 1];
  } else {
    pages = [0, current - 1, current, current + 1, total - 1];
  }
  const items: PageWindowItem[] = [];
  for (const [index, value] of pages.entries()) {
    if (index > 0 && value - pages[index - 1] > 1) {
      items.push(index === 1 ? "ellipsis-start" : "ellipsis-end");
    }
    items.push(value);
  }
  return { page: current, pageCount: total, items };
}
