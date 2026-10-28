"use client";

import { type ReactNode, useEffect, useRef } from "react";
import styles from "./home.module.css";
import { getHomeMotion } from "./home-motion";

export function HomeExperience({ children }: { children: ReactNode }) {
  const root = useRef<HTMLElement>(null);
  useEffect(() => {
    const page = root.current;
    if (!page) return;
    const hero = page.querySelector<HTMLElement>('[data-scene="hero"]');
    const chapter = page.querySelector<HTMLElement>('[data-scene="chapter"]');
    if (!hero || !chapter) return;
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const compact = window.matchMedia("(max-width: 700px)");
    const connection = (
      navigator as Navigator & {
        connection?: EventTarget & { saveData?: boolean };
      }
    ).connection;
    const reveals = [...page.querySelectorAll<HTMLElement>("[data-reveal]")];
    let frame = 0;
    let enabled = false;
    let observer: IntersectionObserver | undefined;
    const reset = () => {
      page.removeAttribute("data-motion");
      for (const property of [
        "--hero-shift",
        "--copy-shift",
        "--copy-opacity",
        "--chapter-shift",
      ])
        page.style.removeProperty(property);
      for (const item of reveals) item.setAttribute("data-reveal", "visible");
    };
    const paint = () => {
      frame = 0;
      if (!enabled || document.hidden) return;
      // Read geometry before writing styles; no React render on scroll.
      const heroRect = hero.getBoundingClientRect();
      const chapterRect = chapter.getBoundingClientRect();
      const motion = getHomeMotion({
        heroTop: heroRect.top,
        heroHeight: heroRect.height,
        chapterTop: chapterRect.top,
        chapterHeight: chapterRect.height,
        viewportHeight: window.innerHeight,
        compact: compact.matches,
      });
      page.style.setProperty(
        "--hero-shift",
        `${motion.heroShift.toFixed(2)}px`,
      );
      page.style.setProperty(
        "--copy-shift",
        `${motion.copyShift.toFixed(2)}px`,
      );
      page.style.setProperty("--copy-opacity", motion.copyOpacity.toFixed(3));
      page.style.setProperty(
        "--chapter-shift",
        `${motion.chapterShift.toFixed(2)}px`,
      );
    };
    const schedule = () => {
      if (enabled && !document.hidden && !frame)
        frame = window.requestAnimationFrame(paint);
    };
    const configure = () => {
      enabled = !preference.matches && !connection?.saveData;
      observer?.disconnect();
      window.cancelAnimationFrame(frame);
      frame = 0;
      reset();
      if (!enabled) return;
      page.setAttribute("data-motion", "on");
      if ("IntersectionObserver" in window) {
        observer = new IntersectionObserver(
          (entries) => {
            for (const entry of entries) {
              if (!entry.isIntersecting) continue;
              entry.target.setAttribute("data-reveal", "visible");
              observer?.unobserve(entry.target);
            }
          },
          { threshold: 0.08 },
        );
        for (const item of reveals) {
          // Content is visible without JavaScript, and never hidden above the fold.
          if (item.getBoundingClientRect().top <= window.innerHeight - 24)
            continue;
          item.setAttribute("data-reveal", "waiting");
          observer.observe(item);
        }
      }
      schedule();
    };
    const focus = (event: FocusEvent) => {
      if (!(event.target instanceof Element)) return;
      const item = event.target.closest('[data-reveal="waiting"]');
      if (item) {
        item.setAttribute("data-reveal", "visible");
        observer?.unobserve(item);
      }
    };
    configure();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    document.addEventListener("visibilitychange", schedule);
    page.addEventListener("focusin", focus);
    preference.addEventListener("change", configure);
    connection?.addEventListener("change", configure);
    return () => {
      window.cancelAnimationFrame(frame);
      observer?.disconnect();
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      document.removeEventListener("visibilitychange", schedule);
      page.removeEventListener("focusin", focus);
      preference.removeEventListener("change", configure);
      connection?.removeEventListener("change", configure);
      reset();
    };
  }, []);

  return (
    <main ref={root} className={styles.page} data-page="home">
      {children}
    </main>
  );
}
