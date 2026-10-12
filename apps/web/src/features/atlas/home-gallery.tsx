"use client";

import {
  type CSSProperties,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import styles from "./home.module.css";
import { type GalleryLabels, HOME_SCENES } from "./home-scenes";

export function HomeGallery({ labels }: { labels: GalleryLabels }) {
  const [active, setActive] = useState(0);
  const [mounted, setMounted] = useState([0]);
  const [ready, setReady] = useState<number[]>([]);
  const [failed, setFailed] = useState<number[]>([]);
  const [playing, setPlaying] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [requested, setRequested] = useState<number | null>(null);
  const request = useRef<number | null>(null);
  const imageReady = useCallback((index: number) => {
    setReady((images) =>
      images.includes(index) ? images : [...images, index],
    );
    if (request.current === index) {
      setActive(index);
      request.current = null;
      setRequested(null);
    }
  }, []);

  useEffect(() => {
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const connection = (
      navigator as Navigator & {
        connection?: { saveData?: boolean };
      }
    ).connection;
    setPlaying(!motion.matches && !connection?.saveData);
    const visibility = () => setHidden(document.hidden);
    const preference = () => {
      if (motion.matches) setPlaying(false);
    };
    visibility();
    document.addEventListener("visibilitychange", visibility);
    motion.addEventListener("change", preference);
    return () => {
      document.removeEventListener("visibilitychange", visibility);
      motion.removeEventListener("change", preference);
    };
  }, []);

  const choose = useCallback(
    (index: number, manual = false) => {
      if (manual) setPlaying(false);
      if (failed.includes(index)) return;
      if (ready.includes(index)) {
        request.current = null;
        setRequested(null);
        setActive(index);
      } else {
        request.current = index;
        setRequested(index);
        setMounted((images) => [...new Set([...images, index])]);
      }
    },
    [ready, failed],
  );

  useEffect(() => {
    if (
      !playing ||
      hidden ||
      hovered ||
      focused ||
      requested !== null ||
      !ready.includes(active)
    )
      return;
    const next = [1, 2]
      .map((offset) => (active + offset) % HOME_SCENES.length)
      .find((index) => !failed.includes(index));
    if (next === undefined) return;
    const timer = window.setTimeout(() => choose(next), 8500);
    return () => window.clearTimeout(timer);
  }, [
    active,
    choose,
    failed,
    hidden,
    hovered,
    focused,
    playing,
    ready,
    requested,
  ]);

  const scene = HOME_SCENES[active];
  return (
    <fieldset
      className={styles.gallery}
      aria-label={labels.galleryLabel}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget))
          setFocused(false);
      }}
    >
      {mounted.map((index) => {
        const image = HOME_SCENES[index];
        return (
          <picture
            key={image.key}
            className={`${styles.image} ${active === index ? styles.visible : ""}`}
            style={{ "--photo-position": image.position } as CSSProperties}
          >
            <source
              media="(max-width: 700px)"
              srcSet={`/images/uae/${image.image}-768.webp`}
            />
            <img
              src={`/images/uae/${image.image}-1920.webp`}
              alt=""
              width="1920"
              height={image.height}
              decoding="async"
              fetchPriority={index === 0 ? "high" : "low"}
              ref={(element) => {
                if (element?.complete && element.naturalWidth > 0)
                  imageReady(index);
              }}
              onLoad={() => imageReady(index)}
              onError={() => {
                setFailed((images) => [...new Set([...images, index])]);
                if (request.current === index) {
                  request.current = null;
                  setRequested(null);
                }
              }}
            />
          </picture>
        );
      })}
      <div className={styles.shade} />
      <div className={styles.galleryFooter}>
        <div className={styles.photoCaption}>
          <span className={styles.captionIndex} aria-hidden="true">
            0{active + 1} / 03
          </span>
          <div>
            <span className={styles.captionTitle}>{labels[scene.key]}</span>
            <a href={scene.url} target="_blank" rel="noopener noreferrer">
              {labels.photoCredit}: <bdi>{scene.photographer}</bdi> / Unsplash
            </a>
          </div>
        </div>
        <div className={styles.galleryControls}>
          {HOME_SCENES.map((image, index) => (
            <button
              key={image.key}
              type="button"
              aria-pressed={active === index}
              disabled={failed.includes(index)}
              onClick={() => choose(index, true)}
              className={styles.sceneButton}
            >
              <span className={styles.sceneLine} aria-hidden="true" />
              {labels[image.key]}
            </button>
          ))}
          <button
            type="button"
            className={styles.playButton}
            aria-label={playing ? labels.pause : labels.play}
            onClick={() => setPlaying((value) => !value)}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              {playing ? (
                <path d="M8 6v12M16 6v12" />
              ) : (
                <path d="m9 6 9 6-9 6Z" />
              )}
            </svg>
          </button>
        </div>
      </div>
    </fieldset>
  );
}
