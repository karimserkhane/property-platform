"use client";

import { useEffect, useRef } from "react";
import { pageWindow } from "./page-window";

export function AtlasPagination({
  page,
  pageCount,
  onPageChange,
  label,
  previousLabel,
  nextLabel,
  locale,
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  label: string;
  previousLabel: string;
  nextLabel: string;
  locale: string;
}) {
  const pagination = pageWindow(page, pageCount);
  const currentButton = useRef<HTMLButtonElement>(null);
  const initiatingControl = useRef<HTMLButtonElement | null>(null);
  // biome-ignore lint/correctness/useExhaustiveDependencies: restore focus after the controlled page or list length changes.
  useEffect(() => {
    const control = initiatingControl.current;
    initiatingControl.current = null;
    if (!control || (control.isConnected && !control.disabled)) return;
    // Reaching an endpoint disables Previous/Next. Keep keyboard focus nearby,
    // unless the user has already moved it outside this pagination.
    if (
      document.activeElement === control ||
      document.activeElement === document.body
    ) {
      currentButton.current?.focus({ preventScroll: true });
    }
  }, [pagination.page, pagination.pageCount]);
  function change(control: HTMLButtonElement, nextPage: number) {
    initiatingControl.current = control;
    onPageChange(nextPage);
  }
  if (!pagination.pageCount) return null;
  const numbers = new Intl.NumberFormat(locale);
  return (
    <nav className="atlas-pagination" aria-label={label}>
      <button
        type="button"
        disabled={pagination.page === 0}
        onClick={(event) => change(event.currentTarget, pagination.page - 1)}
      >
        {previousLabel}
      </button>
      {pagination.items.map((item) =>
        typeof item === "number" ? (
          <button
            type="button"
            key={item}
            ref={pagination.page === item ? currentButton : undefined}
            aria-current={pagination.page === item ? "page" : undefined}
            onClick={(event) => change(event.currentTarget, item)}
          >
            <bdi>{numbers.format(item + 1)}</bdi>
          </button>
        ) : (
          <span
            key={item}
            className="atlas-pagination__ellipsis"
            aria-hidden="true"
          >
            …
          </span>
        ),
      )}
      <button
        type="button"
        disabled={pagination.page === pagination.pageCount - 1}
        onClick={(event) => change(event.currentTarget, pagination.page + 1)}
      >
        {nextLabel}
      </button>
    </nav>
  );
}
