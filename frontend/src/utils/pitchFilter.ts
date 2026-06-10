import { hzToMidi } from "./pitch";

export const PITCH_FILTER_CONSTANTS = {
  CONF_THRESHOLD: 0.5,
  HZ_LOW: 60,
  HZ_HIGH: 1000,
  JUMP_SEMITONES: 24,
  // Scaled from prototype's 65 frames at ~23ms/frame (aubio 1024 hop) to preserve
  // ~1.5s silence reset at ~16ms/frame (rAF cadence in the browser).
  SILENCE_RESET_FRAMES: 94,
  TARGET_PROXIMITY: 7,
  SMOOTH_WINDOW: 9,
} as const;

export interface PitchFilterStep {
  /** Post-gate MIDI used to drive lastValid for jump-rejection on the next call. */
  filteredMidi: number | null;
  /** 9-frame nan-median over filteredMidi history — what UI / hit-rate consumes. */
  smoothedMidi: number | null;
}

// Median of the finite values in an array, matching np.nanmedian behaviour:
// odd count → middle element; even count → mean of the two middle elements.
function nanMedian(values: (number | null)[]): number | null {
  const finite = values.filter((v): v is number => v !== null && isFinite(v));
  if (finite.length === 0) return null;
  finite.sort((a, b) => a - b);
  const mid = Math.floor(finite.length / 2);
  if (finite.length % 2 === 1) return finite[mid];
  return (finite[mid - 1] + finite[mid]) / 2;
}

export class PitchFilter {
  private lastValid: number | null = null;
  private silentFrames: number = 0;
  private buf: (number | null)[] = Array(
    PITCH_FILTER_CONSTANTS.SMOOTH_WINDOW,
  ).fill(null);

  step(
    rawHz: number,
    conf: number,
    targetMidi: number | null,
  ): PitchFilterStep {
    const C = PITCH_FILTER_CONSTANTS;
    let filteredMidi: number | null = null;

    // 1. Quality gate
    if (conf <= C.CONF_THRESHOLD || rawHz <= C.HZ_LOW || rawHz >= C.HZ_HIGH) {
      this.silentFrames++;
    } else {
      let raw: number | null = hzToMidi(rawHz);

      // 2. Target proximity + octave fold
      if (targetMidi !== null && !isNaN(targetMidi)) {
        const diff = Math.abs(raw - targetMidi);
        if (diff > C.TARGET_PROXIMITY && Math.abs(diff - 12) > 3) {
          // Music bleed — reject
          raw = null;
        } else if (diff >= 9 && diff <= 15) {
          // Octave fold
          raw = raw < targetMidi ? raw + 12 : raw - 12;
        }
      }

      if (raw !== null) {
        // 3. Jump rejection
        if (
          this.lastValid === null ||
          Math.abs(raw - this.lastValid) <= C.JUMP_SEMITONES
        ) {
          filteredMidi = raw;
          this.lastValid = raw;
          this.silentFrames = 0;
        } else {
          this.silentFrames++;
        }
      } else {
        this.silentFrames++;
      }
    }

    // 4. Silence reset (before buf.append, matching prototype lines 106-110)
    if (this.silentFrames > C.SILENCE_RESET_FRAMES) {
      this.lastValid = null;
      this.silentFrames = 0;
    }

    // 5. Slide the buffer window
    this.buf.push(filteredMidi);
    this.buf.shift();

    // 6. Smoothing
    const smoothedMidi = nanMedian(this.buf);

    return { filteredMidi, smoothedMidi };
  }

  reset(): void {
    this.lastValid = null;
    this.silentFrames = 0;
    this.buf = Array(PITCH_FILTER_CONSTANTS.SMOOTH_WINDOW).fill(null);
  }
}
