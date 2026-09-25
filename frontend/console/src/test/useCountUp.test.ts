import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useCountUp } from "../hooks/useCountUp";

describe("useCountUp", () => {
  let frames: Map<number, FrameRequestCallback>;
  let nextId: number;
  let now: number;

  beforeEach(() => {
    frames = new Map();
    nextId = 0;
    now = 0;
    vi.spyOn(performance, "now").mockImplementation(() => now);
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      frames.set(++nextId, callback);
      return nextId;
    });
    vi.stubGlobal("cancelAnimationFrame", (id: number) => frames.delete(id));
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function advance(time: number) {
    now = time;
    const pending = [...frames.values()];
    frames.clear();
    act(() => pending.forEach((callback) => callback(time)));
  }

  it("finishes at the exact target and cancels on unmount", () => {
    const hook = renderHook(() => useCountUp(100, 100));
    advance(50);
    expect(hook.result.current).toBe(87.5);
    advance(100);
    expect(hook.result.current).toBe(100);
    expect(frames.size).toBe(0);
    hook.unmount();
  });

  it("retargets from the in-progress value with only one active frame", () => {
    const hook = renderHook(({ target }) => useCountUp(target, 100), { initialProps: { target: 100 } });
    advance(50);
    hook.rerender({ target: 200 });
    expect(frames.size).toBe(1);
    advance(100);
    expect(hook.result.current).toBeCloseTo(185.9375);
    hook.unmount();
    expect(frames.size).toBe(0);
  });

  it.each([0, -1, Infinity, NaN])("does not animate invalid duration %s", (duration) => {
    const hook = renderHook(({ target }) => useCountUp(target, duration), { initialProps: { target: 42 } });
    expect(hook.result.current).toBe(42);
    hook.rerender({ target: 84 });
    expect(hook.result.current).toBe(84);
    expect(frames.size).toBe(0);
  });

  it("recovers after a nonfinite target without poisoning the next animation", () => {
    const hook = renderHook(({ target }) => useCountUp(target, 100), { initialProps: { target: Infinity } });
    expect(hook.result.current).toBe(Infinity);
    expect(frames.size).toBe(0);
    hook.rerender({ target: 10 });
    advance(100);
    expect(hook.result.current).toBe(10);
  });
});
