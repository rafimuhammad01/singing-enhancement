package services_test

import (
	"encoding/hex"
	"strings"
	"testing"

	"cantus/backend/services"
)

func TestNewSigner(t *testing.T) {
	tests := []struct {
		name    string
		key     string
		wantErr bool
	}{
		{
			name:    "valid 32-byte key",
			key:     "12345678901234567890123456789012",
			wantErr: false,
		},
		{
			name:    "valid 64-byte key",
			key:     "1234567890123456789012345678901234567890123456789012345678901234",
			wantErr: false,
		},
		{
			name:    "empty key",
			key:     "",
			wantErr: true,
		},
		{
			name:    "key too short 1 byte",
			key:     "a",
			wantErr: true,
		},
		{
			name:    "key too short 16 bytes",
			key:     "1234567890123456",
			wantErr: true,
		},
		{
			name:    "key just shy of 32 bytes",
			key:     "1234567890123456789012345678901",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			signer, err := services.NewSigner(tt.key)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("NewSigner(%q): got nil error, want error", tt.key)
				}
				if !strings.Contains(err.Error(), "32") {
					t.Errorf("NewSigner(%q): error %q does not contain %q", tt.key, err.Error(), "32")
				}
				return
			}

			if err != nil {
				t.Fatalf("NewSigner(%q): got error %v, want nil", tt.key, err)
			}
			if signer == nil {
				t.Errorf("NewSigner(%q): got nil signer, want non-nil", tt.key)
			}
		})
	}
}

func TestSigner_Sign_Deterministic(t *testing.T) {
	signer, err := services.NewSigner("abcdefghijklmnopqrstuvwxyz123456")
	if err != nil {
		t.Fatalf("NewSigner: unexpected error: %v", err)
	}

	tests := []struct {
		name    string
		videoID string
	}{
		{
			name:    "standard youtube video id",
			videoID: "dQw4w9WgXcQ",
		},
		{
			name:    "video id with underscores and hyphens",
			videoID: "abc_def-1_2X",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got1 := signer.Sign(tt.videoID)
			got2 := signer.Sign(tt.videoID)

			if got1 != got2 {
				t.Errorf("Sign(%q) not deterministic: first=%q, second=%q", tt.videoID, got1, got2)
			}

			if len(got1) != 64 {
				t.Errorf("Sign(%q): got length %d, want 64 (hex-encoded SHA-256)", tt.videoID, len(got1))
			}

			if _, err := hex.DecodeString(got1); err != nil {
				t.Errorf("Sign(%q): result %q is not valid hex: %v", tt.videoID, got1, err)
			}
		})
	}
}

func TestSigner_Sign_DifferentVideosDifferentSigs(t *testing.T) {
	signer, err := services.NewSigner("abcdefghijklmnopqrstuvwxyz123456")
	if err != nil {
		t.Fatalf("NewSigner: unexpected error: %v", err)
	}

	tests := []struct {
		name string
		a    string
		b    string
	}{
		{
			name: "different video ids produce different sigs",
			a:    "dQw4w9WgXcQ",
			b:    "aaaaaaaaaaa",
		},
		{
			name: "short vs long-ish video ids",
			a:    "aaaaaaaaaaa",
			b:    "bbbbbbbbbbb",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			sigA := signer.Sign(tt.a)
			sigB := signer.Sign(tt.b)

			if sigA == sigB {
				t.Errorf("Sign(%q) == Sign(%q): both returned %q, want different sigs", tt.a, tt.b, sigA)
			}
		})
	}
}

func TestSigner_Sign_DifferentKeysDifferentSigs(t *testing.T) {
	signer1, err := services.NewSigner("key1key1key1key1key1key1key1key1")
	if err != nil {
		t.Fatalf("NewSigner (signer1): unexpected error: %v", err)
	}

	signer2, err := services.NewSigner("key2key2key2key2key2key2key2key2")
	if err != nil {
		t.Fatalf("NewSigner (signer2): unexpected error: %v", err)
	}

	tests := []struct {
		name    string
		videoID string
	}{
		{
			name:    "same video id signed by different keys",
			videoID: "dQw4w9WgXcQ",
		},
		{
			name:    "another video id signed by different keys",
			videoID: "aaaaaaaaaaa",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			sig1 := signer1.Sign(tt.videoID)
			sig2 := signer2.Sign(tt.videoID)

			if sig1 == sig2 {
				t.Errorf("Sign(%q) with different keys produced same sig %q, want different sigs", tt.videoID, sig1)
			}
		})
	}
}

func TestSigner_Valid(t *testing.T) {
	signer, err := services.NewSigner("abcdefghijklmnopqrstuvwxyz123456")
	if err != nil {
		t.Fatalf("NewSigner: unexpected error: %v", err)
	}

	// Pre-compute signatures needed for dynamic cases.
	goodSig := signer.Sign("dQw4w9WgXcQ")

	// Tamper: flip the last hex character.
	lastChar := goodSig[len(goodSig)-1]
	var tamperedLastChar byte
	if lastChar == '0' {
		tamperedLastChar = '1'
	} else {
		tamperedLastChar = '0'
	}
	tamperedSig := goodSig[:len(goodSig)-1] + string(tamperedLastChar)

	wrongVideoSig := signer.Sign("aaaaaaaaaaa")

	tests := []struct {
		name    string
		videoID string
		sig     string
		want    bool
	}{
		{
			name:    "matching sig",
			videoID: "dQw4w9WgXcQ",
			sig:     goodSig,
			want:    true,
		},
		{
			name:    "tampered sig",
			videoID: "dQw4w9WgXcQ",
			sig:     tamperedSig,
			want:    false,
		},
		{
			name:    "empty sig",
			videoID: "dQw4w9WgXcQ",
			sig:     "",
			want:    false,
		},
		{
			name:    "wrong videoID for sig",
			videoID: "dQw4w9WgXcQ",
			sig:     wrongVideoSig,
			want:    false,
		},
		{
			name:    "non-hex garbage sig",
			videoID: "dQw4w9WgXcQ",
			sig:     "not-hex-garbage!!",
			want:    false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := signer.Valid(tt.videoID, tt.sig)

			if got != tt.want {
				t.Errorf("Valid(%q, %q): got %v, want %v", tt.videoID, tt.sig, got, tt.want)
			}
		})
	}
}
