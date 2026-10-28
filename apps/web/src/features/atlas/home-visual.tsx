import type { CSSProperties } from "react";
import styles from "./home.module.css";
import { HOME_SCENES } from "./home-scenes";

// Decorative photography is static; movement follows the visitor's scroll.
export function HomeVisual() {
  const scene = HOME_SCENES[0];
  return (
    <div className={styles.gallery} aria-hidden="true">
      <div className={styles.heroMedia}>
        <picture
          className={styles.image}
          style={{ "--photo-position": scene.position } as CSSProperties}
        >
          <source
            media="(max-width: 700px)"
            srcSet={`/images/uae/${scene.image}-768.webp`}
          />
          <img
            src={`/images/uae/${scene.image}-1920.webp`}
            alt=""
            width="1920"
            height={scene.height}
            decoding="async"
            fetchPriority="high"
          />
        </picture>
      </div>
      <div className={styles.shade} />
    </div>
  );
}
