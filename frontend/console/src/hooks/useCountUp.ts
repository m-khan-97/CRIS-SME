import { useEffect, useRef, useState } from "react";

const PREFERS_REDUCED_MOTION =
  typeof window !== "undefined" && window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;

/**
 * Animate a numeric value from wherever it currently is to `target`, easing
 * out, so KPI numbers and chart fills sweep in rather than snapping to their
 * final value. Re-targets smoothly (from the in-progress value, not from
 * zero) if `target` changes again before the animation finishes -- e.g. a
 * report reload. Respects prefers-reduced-motion.
 */
export function useCountUp(target: number, durationMs = 700): number {
  const [value, setValue] = useState(PREFERS_REDUCED_MOTION ? target : 0);
  const fromRef = useRef(PREFERS_REDUCED_MOTION ? target : 0);

  useEffect(() => {
    if (PREFERS_REDUCED_MOTION || !Number.isFinite(target)) {
      fromRef.current = target;
      setValue(target);
      return;
    }

    const from = fromRef.current;
    const start = performance.now();
    let frame: number;

    const tick = (now: number) => {
      const progress = Math.min((now - start) / durationMs, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const next = from + (target - from) * eased;
      fromRef.current = next;
      setValue(next);
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      }
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, durationMs]);

  return value;
}
