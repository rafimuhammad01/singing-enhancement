package logger

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5/middleware"
	"github.com/rs/zerolog"
)

// ctxKey is an unexported type for context keys in this package.
type ctxKey struct{}

var loggerKey = ctxKey{}

// New creates a zerolog.Logger writing to out at the given level.
// level must be one of "debug", "info", "warn", "error" (case-sensitive).
func New(out io.Writer, level string) (zerolog.Logger, error) {
	var lvl zerolog.Level
	switch level {
	case "debug":
		lvl = zerolog.DebugLevel
	case "info":
		lvl = zerolog.InfoLevel
	case "warn":
		lvl = zerolog.WarnLevel
	case "error":
		lvl = zerolog.ErrorLevel
	default:
		return zerolog.Nop(), fmt.Errorf("invalid log level %q: must be one of debug/info/warn/error", level)
	}
	return zerolog.New(out).Level(lvl).With().Timestamp().Logger(), nil
}

// WithLogger returns a new context with log stored under the package key.
func WithLogger(ctx context.Context, log zerolog.Logger) context.Context {
	return context.WithValue(ctx, loggerKey, log)
}

// FromCtx retrieves the logger stored by WithLogger.
// Returns a disabled (no-op) logger if none is present.
func FromCtx(ctx context.Context) zerolog.Logger {
	if log, ok := ctx.Value(loggerKey).(zerolog.Logger); ok {
		return log
	}
	return zerolog.Nop()
}

// Middleware returns an HTTP middleware that logs each request as a JSON line.
// The chi middleware.RequestID middleware must run before this one.
func Middleware(log zerolog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			reqID := middleware.GetReqID(r.Context())
			w.Header().Set("X-Request-ID", reqID)

			reqLog := log.With().Str("request_id", reqID).Logger()
			r = r.WithContext(WithLogger(r.Context(), reqLog))

			ww := middleware.NewWrapResponseWriter(w, r.ProtoMajor)
			start := time.Now()

			next.ServeHTTP(ww, r)

			reqLog.Info().
				Str("method", r.Method).
				Str("path", r.URL.Path).
				Int("status", ww.Status()).
				Int64("duration_ms", time.Since(start).Milliseconds()).
				Msg("request")
		})
	}
}
