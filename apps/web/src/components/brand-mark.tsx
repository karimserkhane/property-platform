import { brand } from "@property-platform/branding";
import type { CSSProperties } from "react";

export function BrandMark() {
  return (
    <span
      className="brand-mark"
      aria-hidden="true"
      style={{ "--brand-mark": `url("${brand.webMarkPath}")` } as CSSProperties}
    />
  );
}
