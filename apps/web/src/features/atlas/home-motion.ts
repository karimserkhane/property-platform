type MotionGeometry = {
  heroTop: number;
  heroHeight: number;
  chapterTop: number;
  chapterHeight: number;
  viewportHeight: number;
  compact: boolean;
};

const clamp = (value: number, minimum: number, maximum: number) =>
  Math.min(maximum, Math.max(minimum, value));

// Bounded travel keeps overscanned photographs covering their frames.
export function getHomeMotion(geometry: MotionGeometry) {
  const heroHeight = Math.max(1, geometry.heroHeight);
  const viewportHeight = Math.max(1, geometry.viewportHeight);
  const progress = clamp(-geometry.heroTop / heroHeight, 0, 1);
  const chapterProgress = clamp(
    (viewportHeight / 2 - (geometry.chapterTop + geometry.chapterHeight / 2)) /
      Math.max(1, (viewportHeight + geometry.chapterHeight) / 2),
    -1,
    1,
  );
  return {
    heroShift: progress * (geometry.compact ? 80 : 150),
    copyShift: progress * (geometry.compact ? 16 : 38),
    copyOpacity: 1 - progress * 0.55,
    chapterShift: chapterProgress * (geometry.compact ? 28 : 60),
  };
}
