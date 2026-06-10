const NOTE_NAMES = [
  "C",
  "C#",
  "D",
  "D#",
  "E",
  "F",
  "F#",
  "G",
  "G#",
  "A",
  "A#",
  "B",
];

export function hzToMidi(hz: number): number {
  return 69 + 12 * Math.log2(hz / 440);
}

export function midiToHz(midi: number): number {
  return 440 * Math.pow(2, (midi - 69) / 12);
}

export function midiToNoteName(midi: number): string {
  if (!isFinite(midi)) return "";
  // Round before lookup, matching prototype's int(round(midi_num)) behavior
  const n = Math.round(midi);
  const octave = Math.floor(n / 12) - 1;
  return `${NOTE_NAMES[n % 12]}${octave}`;
}

export function centsOff(hz: number, targetMidi: number): number {
  return (hzToMidi(hz) - targetMidi) * 100;
}
