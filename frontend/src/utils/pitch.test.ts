import { describe, it, expect } from "vitest";
import { hzToMidi, midiToHz, midiToNoteName, centsOff } from "./pitch";

// hzToMidi / midiToHz round-trip
describe("hzToMidi / midiToHz round-trip", () => {
  it.each([21, 33, 45, 57, 60, 69, 72, 81, 84, 96, 108])(
    "midi=%i round-trips through midiToHz then hzToMidi within 1e-9",
    (m) => {
      expect(Math.abs(hzToMidi(midiToHz(m)) - m)).toBeLessThan(1e-9);
    },
  );
});

// midiToNoteName
describe("midiToNoteName", () => {
  it.each([
    [60, "C4"],
    [61, "C#4"],
    [69, "A4"],
    [72, "C5"],
    [45, "A2"],
    [21, "A0"],
    [66, "F#4"],
    [12, "C0"],
    // Negative octave: midi=0 → C-1 (prototype: n//12 - 1 = 0//12 - 1 = -1)
    [0, "C-1"],
    // Non-integer: rounds before lookup
    [60.49, "C4"],
    [60.51, "C#4"],
  ] as [number, string][])("midi %s → %s", (midi, expected) => {
    expect(midiToNoteName(midi)).toBe(expected);
  });

  it.each([NaN, Infinity, -Infinity])(
    'returns "" for non-finite %s',
    (midi) => {
      expect(midiToNoteName(midi)).toBe("");
    },
  );
});

// centsOff
describe("centsOff", () => {
  // Exact match → 0 cents
  it.each([
    [440, 69], // A4 exact
    [261.6255653005986, 60], // C4 exact
  ] as [number, number][])(
    "hz=%s at target midi=%i → 0 cents (exact)",
    (hz, target) => {
      expect(centsOff(hz, target)).toBeCloseTo(0, 9);
    },
  );

  it("hz of midi 69.5 is +50 cents above midi 69", () => {
    const hz = midiToHz(69.5);
    expect(centsOff(hz, 69)).toBeCloseTo(50, 6);
  });

  it("hz of midi 68.5 is -50 cents below midi 69", () => {
    const hz = midiToHz(68.5);
    expect(centsOff(hz, 69)).toBeCloseTo(-50, 6);
  });

  it("hz of midi 70 is +100 cents above midi 69", () => {
    const hz = midiToHz(70);
    expect(centsOff(hz, 69)).toBeCloseTo(100, 6);
  });

  it("hz of midi 68 is -100 cents below midi 69", () => {
    const hz = midiToHz(68);
    expect(centsOff(hz, 69)).toBeCloseTo(-100, 6);
  });
});
