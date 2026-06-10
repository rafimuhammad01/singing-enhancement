package handlers

import "testing"

func TestTransposeKey(t *testing.T) {
	tests := []struct {
		name      string
		key       string
		semitones int
		want      string
	}{
		{name: "A major down 2 → G major", key: "A major", semitones: -2, want: "G major"},
		{name: "C major up 0 → C major", key: "C major", semitones: 0, want: "C major"},
		{name: "B major up 1 → C major (wrap)", key: "B major", semitones: 1, want: "C major"},
		{name: "C major down 1 → B major (wrap)", key: "C major", semitones: -1, want: "B major"},
		{name: "A minor down 7 → D minor (Fake Plastic Trees case)", key: "A minor", semitones: -7, want: "D minor"},
		{name: "F# major up 5 → B major", key: "F# major", semitones: 5, want: "B major"},
		{name: "C major up 12 → C major (octave wraps)", key: "C major", semitones: 12, want: "C major"},
		{name: "C major down 12 → C major", key: "C major", semitones: -12, want: "C major"},
		{name: "empty key → empty", key: "", semitones: 3, want: ""},
		{name: "malformed key → empty", key: "Garbage", semitones: 3, want: ""},
		{name: "mode preserved (minor)", key: "E minor", semitones: 3, want: "G minor"},
		{name: "unknown note → empty", key: "H major", semitones: 0, want: ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := transposeKey(tt.key, tt.semitones); got != tt.want {
				t.Errorf("transposeKey(%q, %d) = %q, want %q", tt.key, tt.semitones, got, tt.want)
			}
		})
	}
}
