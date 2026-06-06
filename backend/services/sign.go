package services

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
)

const minKeyLen = 32

// Signer signs and validates video IDs using HMAC-SHA256.
type Signer struct {
	key []byte
}

// NewSigner returns a Signer backed by key. key must be at least 32 bytes.
func NewSigner(key string) (*Signer, error) {
	if len(key) < minKeyLen {
		return nil, fmt.Errorf("signing key must be at least 32 bytes, got %d", len(key))
	}
	return &Signer{key: []byte(key)}, nil
}

// Sign returns the hex-encoded HMAC-SHA256 of videoID.
func (s *Signer) Sign(videoID string) string {
	mac := hmac.New(sha256.New, s.key)
	mac.Write([]byte(videoID))
	return hex.EncodeToString(mac.Sum(nil))
}

// Valid reports whether sig is the correct HMAC-SHA256 signature for videoID.
func (s *Signer) Valid(videoID, sig string) bool {
	provided, err := hex.DecodeString(sig)
	if err != nil {
		return false
	}
	mac := hmac.New(sha256.New, s.key)
	mac.Write([]byte(videoID))
	expected := mac.Sum(nil)
	// hmac.Equal is constant-time and length-safe.
	return hmac.Equal(expected, provided)
}
