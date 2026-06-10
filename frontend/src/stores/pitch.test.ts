import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { usePitchStore } from "./pitch";

beforeEach(() => {
  setActivePinia(createPinia());
});

// ---------------------------------------------------------------------------
// A. recordSample — hit/total table
// ---------------------------------------------------------------------------
describe("A. recordSample — hit/total", () => {
  it.each<[string, number | null, number | null, number, number]>([
    ["exact match", 60.0, 60.0, 1, 1],
    ["within green band", 60.0, 61.0, 1, 1],
    ["within yellow band", 60.0, 62.5, 1, 1],
    ["boundary ≤3.0", 60.0, 63.0, 1, 1],
    ["just outside 3.01", 60.0, 63.01, 0, 1],
    ["below boundary -3.0", 57.0, 60.0, 1, 1],
    ["user null", null, 60.0, 0, 0],
    ["target null", 60.0, null, 0, 0],
    ["user NaN", NaN, 60.0, 0, 0],
    ["target NaN", 60.0, NaN, 0, 0],
    ["both null", null, null, 0, 0],
  ])(
    "%s: user=%s target=%s → hitDelta=%s totalDelta=%s",
    (_label, userMidi, targetMidi, expectedHitDelta, expectedTotalDelta) => {
      const store = usePitchStore();
      store.recordSample(0, userMidi, targetMidi);
      expect(store.frameHits).toBe(expectedHitDelta);
      expect(store.frameTotal).toBe(expectedTotalDelta);
    },
  );
});

// ---------------------------------------------------------------------------
// B. recordSample always pushes to userTimes/userMidis
// ---------------------------------------------------------------------------
describe("B. recordSample always pushes arrays", () => {
  it("3 samples (voiced+target, voiced-no-target, unvoiced-no-target) → length 3", () => {
    const store = usePitchStore();
    store.recordSample(0.0, 60.0, 60.0); // voiced + target
    store.recordSample(0.1, 62.0, null); // voiced, no target
    store.recordSample(0.2, null, null); // unvoiced, no target
    expect(store.userTimes.length).toBe(3);
    expect(store.userMidis).toEqual([60.0, 62.0, null]);
  });
});

// ---------------------------------------------------------------------------
// C. currentMidi is updated to whatever was passed (including null)
// ---------------------------------------------------------------------------
describe("C. currentMidi tracking", () => {
  it("reflects last smoothedUserMidi, even when null", () => {
    const store = usePitchStore();
    store.recordSample(0.0, 60.0, null);
    expect(store.currentMidi).toBe(60.0);
    store.recordSample(0.1, null, null);
    expect(store.currentMidi).toBeNull();
    store.recordSample(0.2, 72.5, null);
    expect(store.currentMidi).toBe(72.5);
  });
});

// ---------------------------------------------------------------------------
// D. trimSinceSeek truncation cases
// ---------------------------------------------------------------------------
describe("D. trimSinceSeek", () => {
  function populateStore(
    store: ReturnType<typeof usePitchStore>,
    times: number[],
    midis: (number | null)[],
  ) {
    times.forEach((t, i) => store.recordSample(t, midis[i] ?? null, null));
  }

  it.each<[string, number, number, number[]]>([
    ["trim at 2.5 → keep indices 0,1", 2.5, 2, [1, 2]],
    ["trim at 0.5 → keep none", 0.5, 0, []],
    ["trim at 5.5 → no-op, keep all 5", 5.5, 5, [1, 2, 3, 4, 5]],
    ["trim at exact 3.0 → keep indices 0,1 (3.0 removed)", 3.0, 2, [1, 2]],
  ])("%s", (_label, trimAt, expectedLen, expectedTimes) => {
    const store = usePitchStore();
    populateStore(store, [1, 2, 3, 4, 5], [60, 60, 60, 60, 60]);
    store.trimSinceSeek(trimAt);
    expect(store.userTimes.length).toBe(expectedLen);
    expect(store.userMidis.length).toBe(expectedLen);
    expect(store.userTimes).toEqual(expectedTimes);
  });

  it("trim with empty arrays — no throw", () => {
    const store = usePitchStore();
    expect(() => store.trimSinceSeek(1.0)).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// E. trimSinceSeek does NOT reset hits/total
// ---------------------------------------------------------------------------
describe("E. trimSinceSeek preserves frameHits/frameTotal", () => {
  it("100 voiced on-target samples then trim — hits/total unchanged", () => {
    const store = usePitchStore();
    for (let i = 0; i < 100; i++) {
      store.recordSample(i * 0.1, 60.0, 60.0);
    }
    const hitsBefore = store.frameHits;
    const totalBefore = store.frameTotal;
    store.trimSinceSeek(0);
    expect(store.frameHits).toBe(hitsBefore);
    expect(store.frameTotal).toBe(totalBefore);
    expect(store.userTimes.length).toBe(0); // arrays were cleared
  });
});

// ---------------------------------------------------------------------------
// F. hitRate gating (null until frameTotal > 30)
// ---------------------------------------------------------------------------
describe("F. hitRate gating", () => {
  it.each<[string, number, number, number | null]>([
    ["frameTotal=0", 0, 0, null],
    ["frameTotal=30 (boundary, still null)", 30, 15, null],
    ["frameTotal=31", 31, 15, 15 / 31],
    ["frameTotal=100, hits=80", 100, 80, 0.8],
  ])("%s → hitRate=%s", (_label, total, hits, expected) => {
    const store = usePitchStore();
    // Directly drive frameTotal and frameHits via recordSample
    // Use target=60 for on-target hits and target=100 for misses
    for (let i = 0; i < hits; i++) {
      store.recordSample(i * 0.01, 60.0, 60.0); // hit
    }
    for (let i = hits; i < total; i++) {
      store.recordSample(i * 0.01, 60.0, 70.0); // miss (diff=10 > 3.0)
    }
    if (expected === null) {
      expect(store.hitRate).toBeNull();
    } else {
      expect(store.hitRate).toBeCloseTo(expected, 10);
    }
  });
});

// ---------------------------------------------------------------------------
// G. reset() clears state but not isActive
// ---------------------------------------------------------------------------
describe("G. reset()", () => {
  it("clears arrays/counts/currentMidi but leaves isActive=true", () => {
    const store = usePitchStore();
    store.setActive(true);
    for (let i = 0; i < 5; i++) {
      store.recordSample(i * 0.1, 60.0, 60.0);
    }
    store.reset();
    expect(store.userTimes).toEqual([]);
    expect(store.userMidis).toEqual([]);
    expect(store.frameHits).toBe(0);
    expect(store.frameTotal).toBe(0);
    expect(store.currentMidi).toBeNull();
    expect(store.isActive).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// H. setActive flips the flag
// ---------------------------------------------------------------------------
describe("H. setActive", () => {
  it("toggles isActive correctly", () => {
    const store = usePitchStore();
    expect(store.isActive).toBe(false);
    store.setActive(true);
    expect(store.isActive).toBe(true);
    store.setActive(false);
    expect(store.isActive).toBe(false);
  });
});
