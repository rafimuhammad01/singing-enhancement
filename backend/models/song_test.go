package models_test

import (
	"encoding/json"
	"testing"

	"cantus/backend/models"
)

func TestSearchResult_JSONRoundTrip(t *testing.T) {
	tests := []struct {
		name string
		in   models.SearchResult
	}{
		{
			name: "all fields populated",
			in: models.SearchResult{
				VideoID:      "dQw4w9WgXcQ",
				Sig:          "abc123sig",
				Title:        "Never Gonna Give You Up",
				Artist:       "Rick Astley",
				Album:        "Whenever You Need Somebody",
				DurationSec:  213,
				ThumbnailURL: "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Marshal to JSON.
			data, err := json.Marshal(tt.in)
			if err != nil {
				t.Fatalf("json.Marshal error: %v", err)
			}

			// Unmarshal back into struct and verify field preservation.
			var got models.SearchResult
			if err := json.Unmarshal(data, &got); err != nil {
				t.Fatalf("json.Unmarshal error: %v", err)
			}

			if got.VideoID != tt.in.VideoID {
				t.Errorf("VideoID: got %q, want %q", got.VideoID, tt.in.VideoID)
			}
			if got.Sig != tt.in.Sig {
				t.Errorf("Sig: got %q, want %q", got.Sig, tt.in.Sig)
			}
			if got.Title != tt.in.Title {
				t.Errorf("Title: got %q, want %q", got.Title, tt.in.Title)
			}
			if got.Artist != tt.in.Artist {
				t.Errorf("Artist: got %q, want %q", got.Artist, tt.in.Artist)
			}
			if got.Album != tt.in.Album {
				t.Errorf("Album: got %q, want %q", got.Album, tt.in.Album)
			}
			if got.DurationSec != tt.in.DurationSec {
				t.Errorf("DurationSec: got %d, want %d", got.DurationSec, tt.in.DurationSec)
			}
			if got.ThumbnailURL != tt.in.ThumbnailURL {
				t.Errorf("ThumbnailURL: got %q, want %q", got.ThumbnailURL, tt.in.ThumbnailURL)
			}

			// Decode into map to verify exact snake_case JSON keys.
			var m map[string]any
			if err := json.Unmarshal(data, &m); err != nil {
				t.Fatalf("json.Unmarshal into map error: %v", err)
			}

			expectedKeys := []string{
				"video_id",
				"sig",
				"title",
				"artist",
				"album",
				"duration_sec",
				"thumbnail_url",
			}
			for _, key := range expectedKeys {
				if _, ok := m[key]; !ok {
					t.Errorf("JSON key %q missing from encoded output", key)
				}
			}

			if got, want := m["video_id"], tt.in.VideoID; got != want {
				t.Errorf("JSON video_id: got %v, want %v", got, want)
			}
			if got, want := m["thumbnail_url"], tt.in.ThumbnailURL; got != want {
				t.Errorf("JSON thumbnail_url: got %v, want %v", got, want)
			}
			if got, want := m["duration_sec"], float64(tt.in.DurationSec); got != want {
				t.Errorf("JSON duration_sec: got %v, want %v", got, want)
			}
		})
	}
}
