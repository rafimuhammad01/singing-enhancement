package handlers

import (
	"encoding/json"
	"net/http"
	"os"

	"github.com/go-chi/chi/v5"

	"cantus/backend/logger"
	"cantus/backend/services"
)

// previewKeyResponse is the JSON shape returned by the PreviewKey handler.
type previewKeyResponse struct {
	Key string `json:"key"`
}

// PreviewKey returns an http.HandlerFunc that estimates the song's key from the 30s preview.
func PreviewKey(
	signer *services.Signer,
	storage services.Storage,
	ytSvc services.YouTubeService,
	processor services.ProcessorClient,
) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		videoID := chi.URLParam(r, "videoId")
		if !services.ValidVideoID(videoID) {
			writeJSON(w, http.StatusBadRequest, errorResponse{Error: "invalid videoId"})
			return
		}

		sig := r.URL.Query().Get("sig")
		if !signer.Valid(videoID, sig) {
			writeJSON(w, http.StatusBadRequest, errorResponse{Error: "invalid sig"})
			return
		}

		ctx := r.Context()
		log := logger.FromCtx(ctx)

		// Cache check.
		cached, err := storage.Has(ctx, videoID, "preview-key.json")
		if err != nil {
			log.Error().Err(err).Str("videoId", videoID).Msg("storage.Has (preview-key) failed")
			writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "storage check failed"})
			return
		}

		if cached {
			rc, err := storage.Open(ctx, videoID, "preview-key.json")
			if err != nil {
				log.Error().Err(err).Str("videoId", videoID).Msg("storage.Open (preview-key) failed")
				writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "storage open failed"})
				return
			}
			defer func() { _ = rc.Close() }()
			var resp previewKeyResponse
			if err := json.NewDecoder(rc).Decode(&resp); err != nil {
				log.Error().Err(err).Str("videoId", videoID).Msg("preview-key decode failed")
				writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "preview-key parse failed"})
				return
			}
			writeJSON(w, http.StatusOK, resp)
			return
		}

		// Ensure preview.mp3 exists.
		previewExists, err := storage.Has(ctx, videoID, "preview.mp3")
		if err != nil {
			log.Error().Err(err).Str("videoId", videoID).Msg("storage.Has (preview.mp3) failed")
			writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "storage check failed"})
			return
		}

		if !previewExists {
			if err := ytSvc.DownloadPreview(ctx, videoID); err != nil {
				log.Error().Err(err).Str("videoId", videoID).Msg("DownloadPreview failed")
				writeJSON(w, http.StatusBadGateway, errorResponse{Error: "download failed"})
				return
			}
		}

		inputPath, err := storage.LocalPath(ctx, videoID, "preview.mp3")
		if err != nil {
			log.Error().Err(err).Str("videoId", videoID).Msg("storage.LocalPath failed")
			writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "storage path failed"})
			return
		}

		key, err := processor.PreviewKey(ctx, inputPath)
		if err != nil {
			log.Error().Err(err).Str("videoId", videoID).Msg("processor.PreviewKey failed")
			writeJSON(w, http.StatusBadGateway, errorResponse{Error: "preview-key estimation failed"})
			return
		}

		// Persist result to cache via temp file.
		tmp, err := os.CreateTemp("", "cantus-preview-key-*")
		if err != nil {
			log.Error().Err(err).Str("videoId", videoID).Msg("os.CreateTemp failed")
			writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "storage temp failed"})
			return
		}
		tmpPath := tmp.Name()
		defer func() { _ = os.Remove(tmpPath) }()

		if err := json.NewEncoder(tmp).Encode(previewKeyResponse{Key: key}); err != nil {
			_ = tmp.Close()
			log.Error().Err(err).Str("videoId", videoID).Msg("encode preview-key to temp failed")
			writeJSON(w, http.StatusInternalServerError, errorResponse{Error: "storage encode failed"})
			return
		}
		_ = tmp.Close()

		if err := storage.Commit(ctx, videoID, "preview-key.json", tmpPath); err != nil {
			log.Error().Err(err).Str("videoId", videoID).Msg("storage.Commit (preview-key) failed")
		}

		writeJSON(w, http.StatusOK, previewKeyResponse{Key: key})
	}
}
