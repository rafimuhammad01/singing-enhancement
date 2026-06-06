package api

import (
	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
	"github.com/rs/zerolog"

	"cantus/backend/api/handlers"
	"cantus/backend/logger"
)

// NewRouter builds and returns the chi router with all middleware and routes.
func NewRouter(allowedOrigins []string, log zerolog.Logger) *chi.Mux {
	mux := chi.NewRouter()

	mux.Use(middleware.RequestID)
	mux.Use(logger.Middleware(log))
	mux.Use(cors.Handler(cors.Options{
		AllowedOrigins:   allowedOrigins,
		AllowedMethods:   []string{"GET", "POST", "OPTIONS"},
		AllowedHeaders:   []string{"Content-Type"},
		AllowCredentials: false,
		MaxAge:           300,
	}))

	mux.Get("/health", handlers.Health)
	return mux
}
