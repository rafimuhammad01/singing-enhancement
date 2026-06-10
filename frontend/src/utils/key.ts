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

/** Transpose "A major" / "C minor" by N semitones. Returns "" for empty/malformed. */
export function transposeKey(key: string, semitones: number): string {
  if (!key) return "";
  const parts = key.split(" ");
  if (parts.length !== 2) return "";
  const [note, mode] = parts;
  const idx = NOTE_NAMES.indexOf(note);
  if (idx === -1) return "";
  const newIdx = (((idx + semitones) % 12) + 12) % 12;
  return `${NOTE_NAMES[newIdx]} ${mode}`;
}

/** Render "A major" → "A", "F# minor" → "F#m", "" → "". */
export function shortKey(key: string): string {
  if (!key) return "";
  const parts = key.split(" ");
  if (parts.length !== 2) return key;
  const [note, mode] = parts;
  return mode === "minor" ? `${note}m` : note;
}
