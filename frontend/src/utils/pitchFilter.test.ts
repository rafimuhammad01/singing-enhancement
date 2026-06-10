import { describe, it, expect } from "vitest";
import { PitchFilter, PITCH_FILTER_CONSTANTS } from "./pitchFilter";
import { hzToMidi, midiToHz } from "./pitch";

const C = PITCH_FILTER_CONSTANTS;

// ---------------------------------------------------------------------------
// A. Quality gate — all reject on the first call (empty buf → smoothedMidi null)
// ---------------------------------------------------------------------------
describe("A. Quality gate", () => {
  it.each([
    ["low conf", 0.4, 300],
    ["out-of-band low hz", 0.6, 50],
    ["out-of-band high hz boundary (>=)", 0.6, C.HZ_HIGH],
    ["out-of-band low hz boundary (<=)", 0.6, C.HZ_LOW],
  ])(
    "%s: conf=%s hz=%s → filteredMidi null, smoothedMidi null",
    (_label, conf, hz) => {
      const f = new PitchFilter();
      const { filteredMidi, smoothedMidi } = f.step(hz, conf, null);
      expect(filteredMidi).toBeNull();
      expect(smoothedMidi).toBeNull();
    },
  );
});

// ---------------------------------------------------------------------------
// B. Quality pass, no target — filteredMidi = hzToMidi(rawHz)
// ---------------------------------------------------------------------------
describe("B. Quality pass, no target", () => {
  it("440 Hz, conf 0.9, targetMidi null → filteredMidi ≈ 69", () => {
    const f = new PitchFilter();
    const { filteredMidi } = f.step(440, 0.9, null);
    expect(filteredMidi).not.toBeNull();
    expect(filteredMidi!).toBeCloseTo(hzToMidi(440), 6);
  });
});

// ---------------------------------------------------------------------------
// C. Target proximity reject
// ---------------------------------------------------------------------------
describe("C. Target proximity reject", () => {
  it("targetMidi=60, raw midi 68 (diff=8, |8-12|=4 >3) → reject → filteredMidi null", () => {
    const f = new PitchFilter();
    const hz = midiToHz(68);
    const { filteredMidi } = f.step(hz, 0.9, 60);
    expect(filteredMidi).toBeNull();
  });

  it("targetMidi=60, raw midi 70 (diff=10, |10-12|=2 ≤3) → fold, NOT reject", () => {
    const f = new PitchFilter();
    const hz = midiToHz(70);
    const { filteredMidi } = f.step(hz, 0.9, 60);
    // diff=10, 9≤10≤15 → fold: raw(70) > target(60) → raw-12 = 58
    expect(filteredMidi).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// D. Conjunction edge — diff=9, |9-12|=3, NOT >3 → not rejected, fold applied
// ---------------------------------------------------------------------------
describe("D. Conjunction edge", () => {
  it("targetMidi=60, raw midi 69 (diff=9, |9-12|=3 not >3 → not rejected; 9≤9≤15 → fold to 57)", () => {
    const f = new PitchFilter();
    const hz = midiToHz(69);
    const { filteredMidi } = f.step(hz, 0.9, 60);
    // raw(69) > target(60) → 69-12 = 57
    expect(filteredMidi).toBeCloseTo(57, 6);
  });
});

// ---------------------------------------------------------------------------
// E. Octave fold up — raw < target
// ---------------------------------------------------------------------------
describe("E. Octave fold up", () => {
  it("targetMidi=60, raw midi 50 (diff=10, |10-12|=2 ≤3 → fold; raw<target → raw+12=62)", () => {
    const f = new PitchFilter();
    const hz = midiToHz(50);
    const { filteredMidi } = f.step(hz, 0.9, 60);
    expect(filteredMidi).toBeCloseTo(62, 6);
  });
});

// ---------------------------------------------------------------------------
// F. Octave fold down — raw > target
// ---------------------------------------------------------------------------
describe("F. Octave fold down", () => {
  it("targetMidi=60, raw midi 70 (diff=10, |10-12|=2 ≤3 → fold; raw>target → raw-12=58)", () => {
    const f = new PitchFilter();
    const hz = midiToHz(70);
    const { filteredMidi } = f.step(hz, 0.9, 60);
    expect(filteredMidi).toBeCloseTo(58, 6);
  });
});

// ---------------------------------------------------------------------------
// G. No fold inside proximity — diff ≤ TARGET_PROXIMITY
// ---------------------------------------------------------------------------
describe("G. No fold inside proximity", () => {
  it("targetMidi=60, raw midi 65 (diff=5 ≤7 → no fold) → filteredMidi ≈ 65", () => {
    const f = new PitchFilter();
    const hz = midiToHz(65);
    const { filteredMidi } = f.step(hz, 0.9, 60);
    expect(filteredMidi).toBeCloseTo(65, 6);
  });
});

// ---------------------------------------------------------------------------
// H. Jump rejection
// ---------------------------------------------------------------------------
describe("H. Jump rejection", () => {
  it("accept raw 60 then raw 90 (diff 30 > 24) → second call filteredMidi null", () => {
    const f = new PitchFilter();
    f.step(midiToHz(60), 0.9, null);
    const { filteredMidi } = f.step(midiToHz(90), 0.9, null);
    expect(filteredMidi).toBeNull();
  });

  it("accept raw 48 then raw 72 (diff 24 = JUMP_SEMITONES, ≤ → accepted)", () => {
    // midi 48 ≈ 131 Hz, midi 72 ≈ 523 Hz — both within HZ range
    const f = new PitchFilter();
    f.step(midiToHz(48), 0.9, null);
    const { filteredMidi } = f.step(midiToHz(72), 0.9, null);
    expect(filteredMidi).toBeCloseTo(72, 6);
  });
});

// ---------------------------------------------------------------------------
// I. Silence reset
// ---------------------------------------------------------------------------
describe("I. Silence reset", () => {
  it("after SILENCE_RESET_FRAMES+1 rejects, lastValid clears and a clean accept works", () => {
    const f = new PitchFilter();
    // Establish a lastValid far from next pitch so jump would normally reject
    // midi 48 ≈ 131 Hz; midi 73 ≈ 554 Hz — diff 25 > JUMP_SEMITONES(24)
    f.step(midiToHz(48), 0.9, null); // lastValid = 48

    // Feed SILENCE_RESET_FRAMES + 1 bad frames (low conf) to trigger reset
    for (let i = 0; i < C.SILENCE_RESET_FRAMES + 1; i++) {
      f.step(300, 0.1, null); // low conf → rejected → silentFrames++
    }

    // After reset, lastValid is null → jump check always passes → should accept midi 73
    const { filteredMidi } = f.step(midiToHz(73), 0.9, null);
    expect(filteredMidi).toBeCloseTo(73, 6);
  });
});

// ---------------------------------------------------------------------------
// J. 9-frame median smoothing
// ---------------------------------------------------------------------------
describe("J. Smoothing", () => {
  it("9 frames all accepting midi 70 → smoothedMidi === 70", () => {
    const f = new PitchFilter();
    let last: ReturnType<PitchFilter["step"]> | undefined;
    for (let i = 0; i < 9; i++) {
      last = f.step(midiToHz(70), 0.9, null);
    }
    expect(last!.smoothedMidi).toBeCloseTo(70, 6);
  });

  it("mixed buf nulls+values [null,null,60,60,62,62,64,64,64] → smoothedMidi 62", () => {
    // Build a fresh filter and drive it to produce exactly that window.
    // Simplest: use reset() then feed 2 bad + 2×60 + 2×62 + 3×64
    const f = new PitchFilter();
    f.step(midiToHz(60), 0.1, null); // null
    f.step(midiToHz(60), 0.1, null); // null
    f.step(midiToHz(60), 0.9, null); // 60
    f.step(midiToHz(60), 0.9, null); // 60
    f.step(midiToHz(62), 0.9, null); // 62
    f.step(midiToHz(62), 0.9, null); // 62
    f.step(midiToHz(64), 0.9, null); // 64
    f.step(midiToHz(64), 0.9, null); // 64
    const { smoothedMidi } = f.step(midiToHz(64), 0.9, null); // 64
    // 7 finite values: [60,60,62,62,64,64,64] → sorted middle (index 3) = 62
    expect(smoothedMidi).toBeCloseTo(62, 6);
  });

  it("all-null buf (9 low-conf frames) → smoothedMidi null", () => {
    const f = new PitchFilter();
    let last: ReturnType<PitchFilter["step"]> | undefined;
    for (let i = 0; i < 9; i++) {
      last = f.step(300, 0.1, null); // low conf
    }
    expect(last!.smoothedMidi).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// K. Even-count median averaging
// ---------------------------------------------------------------------------
describe("K. Even-count median averaging", () => {
  it("[60,60,62,62,64,64,66,66] + 1 null → mean of two middles = 63", () => {
    // Feed 1 null then 8 accepted values to get the right window shape
    const f = new PitchFilter();
    f.step(300, 0.1, null); // null
    f.step(midiToHz(60), 0.9, null); // 60
    f.step(midiToHz(60), 0.9, null); // 60
    f.step(midiToHz(62), 0.9, null); // 62
    f.step(midiToHz(62), 0.9, null); // 62
    f.step(midiToHz(64), 0.9, null); // 64
    f.step(midiToHz(64), 0.9, null); // 64
    f.step(midiToHz(66), 0.9, null); // 66
    const { smoothedMidi } = f.step(midiToHz(66), 0.9, null); // 66
    // 8 finite values: [60,60,62,62,64,64,66,66] → middles at index 3,4 = (62+64)/2 = 63
    expect(smoothedMidi).toBeCloseTo(63, 6);
  });
});

// ---------------------------------------------------------------------------
// L. reset()
// ---------------------------------------------------------------------------
describe("L. reset()", () => {
  it("after populating state, reset() makes next step identical to fresh instance", () => {
    const used = new PitchFilter();
    // Populate state: establish lastValid and partial buf
    used.step(midiToHz(60), 0.9, null);
    used.step(midiToHz(62), 0.9, null);
    used.step(midiToHz(64), 0.9, null);
    used.reset();

    const fresh = new PitchFilter();
    const r1 = used.step(440, 0.9, null);
    const r2 = fresh.step(440, 0.9, null);

    expect(r1.filteredMidi).toBeCloseTo(r2.filteredMidi!, 6);
    expect(r1.smoothedMidi).toBeCloseTo(r2.smoothedMidi!, 6);
  });
});
