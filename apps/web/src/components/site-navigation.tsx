"use client";

import { useEffect, useRef } from "react";
import { Link, usePathname } from "@/i18n/navigation";
import styles from "./site-navigation.module.css";

type NavigationLink = { href: string; label: string };

/** A regular site navigation, with a native disclosure on compact screens. */
export function SiteNavigation({
  label,
  links,
}: {
  label: string;
  links: NavigationLink[];
}) {
  const pathname = usePathname();
  const disclosure = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    function closeOutside(event: PointerEvent) {
      const menu = disclosure.current;
      if (menu?.open && !menu.contains(event.target as Node)) menu.open = false;
    }
    function closeOnEscape(event: KeyboardEvent) {
      const menu = disclosure.current;
      if (event.key !== "Escape" || !menu?.open) return;
      event.preventDefault();
      menu.open = false;
      menu.querySelector("summary")?.focus();
    }
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  function navigationLinks() {
    return links.map(({ href, label }) => (
      <Link
        key={href}
        href={href}
        aria-current={
          !href.includes("#") &&
          (pathname === href || pathname.startsWith(`${href}/`))
            ? "page"
            : undefined
        }
        onClick={() => {
          if (disclosure.current) disclosure.current.open = false;
        }}
      >
        {label}
      </Link>
    ));
  }

  return (
    <>
      <nav className={styles.desktop} aria-label={label}>
        {navigationLinks()}
      </nav>
      <details
        className={styles.mobile}
        ref={disclosure}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget))
            event.currentTarget.open = false;
        }}
      >
        <summary aria-label={label}>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            aria-hidden="true"
            focusable="false"
          >
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </summary>
        <nav className={styles.panel} aria-label={label}>
          {navigationLinks()}
        </nav>
      </details>
    </>
  );
}
