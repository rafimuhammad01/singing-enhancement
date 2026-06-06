package logger_test

import (
	"bytes"
	"context"
	"io"
	"strings"
	"testing"

	"github.com/rs/zerolog"

	"cantus/backend/logger"
)

// TestNew verifies that New returns a usable zerolog.Logger for valid level
// strings and an error for invalid ones.
func TestNew(t *testing.T) {
	tests := []struct {
		name      string
		level     string
		wantErr   bool
		wantLevel zerolog.Level
	}{
		{
			name:      "debug level",
			level:     "debug",
			wantErr:   false,
			wantLevel: zerolog.DebugLevel,
		},
		{
			name:      "info level",
			level:     "info",
			wantErr:   false,
			wantLevel: zerolog.InfoLevel,
		},
		{
			name:      "warn level",
			level:     "warn",
			wantErr:   false,
			wantLevel: zerolog.WarnLevel,
		},
		{
			name:      "error level",
			level:     "error",
			wantErr:   false,
			wantLevel: zerolog.ErrorLevel,
		},
		{
			name:    "trace is invalid",
			level:   "trace",
			wantErr: true,
		},
		{
			name:    "uppercase INFO is invalid (strict)",
			level:   "INFO",
			wantErr: true,
		},
		{
			name:    "empty string is invalid",
			level:   "",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			log, err := logger.New(io.Discard, tt.level)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("New(%q) returned nil error; want error", tt.level)
				}
				if tt.level != "" && !strings.Contains(err.Error(), tt.level) {
					t.Errorf("error %q should contain the offending level %q", err.Error(), tt.level)
				}
				return
			}
			if err != nil {
				t.Fatalf("New(%q) returned unexpected error: %v", tt.level, err)
			}
			if got := log.GetLevel(); got != tt.wantLevel {
				t.Errorf("logger level: got %v, want %v", got, tt.wantLevel)
			}
		})
	}
}

// TestFromCtx_NoLogger verifies that FromCtx returns a disabled logger when
// no logger has been stored in the context.
func TestFromCtx_NoLogger(t *testing.T) {
	tests := []struct {
		name string
	}{
		{name: "returns disabled logger for bare context"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()
			got := logger.FromCtx(ctx)
			if got.GetLevel() != zerolog.Disabled {
				t.Errorf("FromCtx(bare ctx) level: got %v, want %v (Disabled)", got.GetLevel(), zerolog.Disabled)
			}
		})
	}
}

// TestFromCtx_WithLogger verifies that a logger stored via WithLogger is
// correctly retrieved by FromCtx and is functional.
func TestFromCtx_WithLogger(t *testing.T) {
	tests := []struct {
		name string
	}{
		{name: "retrieves stored logger and it writes output"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var buf bytes.Buffer
			log, err := logger.New(&buf, "info")
			if err != nil {
				t.Fatalf("New() returned unexpected error: %v", err)
			}

			ctx := context.Background()
			ctx2 := logger.WithLogger(ctx, log)
			got := logger.FromCtx(ctx2)

			got.Info().Msg("hello")

			output := buf.String()
			if !strings.Contains(output, "hello") {
				t.Errorf("expected buffer to contain %q after logging; got: %q", "hello", output)
			}
		})
	}
}

// TestMiddleware_Exported verifies that Middleware is exported and returns a
// non-nil handler wrapper. Full request-log-field assertions are in
// router_test.go where the chi middleware chain (including RequestID) is wired.
func TestMiddleware_Exported(t *testing.T) {
	tests := []struct {
		name string
	}{
		{name: "Middleware returns non-nil wrapper"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			log, err := logger.New(io.Discard, "info")
			if err != nil {
				t.Fatalf("New() error: %v", err)
			}
			mw := logger.Middleware(log)
			if mw == nil {
				t.Errorf("Middleware() returned nil")
			}
		})
	}
}
