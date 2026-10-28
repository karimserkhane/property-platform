// A quiet location cue, unrelated to sales activity. No React state per frame.
export function projectPulseFrame(time: number) {
  const phase = (((time % 2400) + 2400) % 2400) / 2400;
  return { radius: 10 + 15 * phase, opacity: 0.24 * (1 - phase) ** 2 };
}
