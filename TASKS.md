# Task Tracker

Full task breakdown for the cantus project. Work through groups in order — each group should be fully functional before starting the next.

Check off tasks as you complete them. When starting a Claude Code session, tell Claude which group you're working on.

## Development Workflow (TDD + Multi-Agent)
Each feature: **Test Agent (red) → Implement (green) → Refactor → repeat** per behavior.
When all group todos are done: **Code Review Agent → pre-commit hooks → commit**.

## Model Strategy
- Planning sessions → **Opus** (`/model`)
- TDD cycles → **Sonnet** (`/model`)
- Code Review Agent → **Opus** (`/model`)

## Core UX Decision (drives architecture)
Users iterate on the **30s preview** (fast, ~1-2s per key) to find the right key. Only commit to the **slow full-song pipeline** (90-180s) when they're happy with the key choice.

- `/api/preview/:videoId` — 30s clip, original key (~5s, cached)
- `/api/preview-shift` { video_id, semitones } — 30s clip pitch-shifted (~1-2s, cached per semitone)
- `/api/generate` { video_id, semitones } — full pipeline with smart caching

---

## Group 1 — Project Setup
- [x] Create CLAUDE.md (run commands, env setup, prerequisite installs)
- [x] Scaffold directory structure (backend/, audio-processor/, frontend/)
- [x] Create per-service .env.example files (backend/ and audio-processor/)
- [x] Update .gitignore
- [x] Set up pre-commit framework: create `.pre-commit-config.yaml`, run `pre-commit install`
- [x] Install Go linting: `brew install golangci-lint` (ruff/black managed by pre-commit — no separate install needed)
- [ ] `npm i -D eslint prettier` in frontend/ (deferred to Group 8 when Vue project exists)
- [x] `brew install yt-dlp ffmpeg` (prerequisite for backend + audio processor)
- [x] Remove Spotify references from CLAUDE.md and .env.example (Spotify was dropped)

## Group 2 — Go Backend Foundation
- [x] Initialize Go module (`go mod init cantus/backend`)
- [x] Chi router with CORS middleware (env-configurable origins) and /health endpoint
- [x] Config loading from .env (`os.Getenv`, fail-fast on missing required vars)
- [x] Models: SearchResult, Job, JobStatus, ProcessRequest
- [x] HMAC signing helpers (`services/sign.go`): Signer.Sign/Valid with `hmac.Equal` constant-time compare, hex-decode rejects non-hex input
- [x] JobStore service (`services/job_store.go`): in-memory map + `sync.RWMutex` + TTL cleanup goroutine (record TTL, not cache files)
- [x] Storage interface + LocalDiskStorage (`services/storage.go`): LocalPath/Has/Commit/Open, TTL-aware cleanup goroutine + empty `{videoID}/` dir pruning
- [x] Structured logging (zerolog) + request-id middleware (`logger/logger.go`): `LOG_LEVEL` config, `X-Request-ID` response header, request-scoped logger via `FromCtx`

## Group 3 — Python Microservice Foundation + Song Search
Reordered ahead of the Go search/preview group because the Go `/api/songs/search` handler proxies through Python's `ytmusicapi` — Python must exist first.
- [x] FastAPI app skeleton with `/health` endpoint
- [x] Create venv (`audio-processor/.venv/`) + `pyproject.toml` (ruff + pytest) + `requirements.txt` (Group 3 deps pinned; heavy ML deps deferred to Group 6)
- [x] Structured JSON logging via `logging_config.setup_logging()` using `pythonjsonlogger.json.JsonFormatter`
- [x] `services/ytmusic_service.py` — `SearchService` wraps `YTMusic.search(query, filter="songs", limit=N)`, maps raw → `{videoId, title, artist, album, duration_sec, thumbnail_url}`, skips entries missing `videoId`, TTLCache(maxsize=256, ttl=600), trims `mapped[:limit]` to defend against ytmusicapi v1.12.1 ignoring `limit`
- [x] `routers/search.py` — `POST /search { query, limit }`, pydantic v2 validation (query 1-200 chars, limit 1-20), `Annotated[SearchService, Depends(get_search_service)]` DI pattern (overridable via `app.dependency_overrides` in tests)
- [x] Manual integration test: `/health` returns `{"status":"ok"}`, `/search` with `query="wish you were here"` returns Pink Floyd / Neck Deep / Avril Lavigne in the top results, exactly `limit` entries returned

## Group 4 — Go Search + Preview Download
- [ ] `YouTubeService.Search(query)` — HTTP POST `python:8090/search`, then HMAC-sign each `videoId` and attach `sig` to each result.
- [ ] `YouTubeService.DownloadPreview(videoId)` — `yt-dlp --download-sections "*0-30"` → 30s MP3 written through Storage interface to `{video_id}/preview.mp3`.
- [ ] Video ID validator: regex `^[A-Za-z0-9_-]{11}$` — runs on every videoId received by ANY handler.
- [ ] `GET /api/songs/search?q=` handler — returns `[]SearchResult` with sig field.
- [ ] `GET /api/preview/:videoId?sig=...` handler — validates sig BEFORE any work; 400 on mismatch. Serves cached preview.mp3 or triggers DownloadPreview on miss.
- [ ] Manual test: search → pick a result → preview with valid sig works; preview with tampered sig (or no sig) returns 400.

## Group 5 — Preview Pitch Shift (fast iteration loop)
- [ ] `POST /api/preview-shift` `{ video_id, sig, semitones }` handler — validate sig FIRST, then proceed
- [ ] Cache lookup via Storage: serve `{video_id}/preview-shifts/{semitones}.mp3` if `Has()` true
- [ ] On cache miss: ensure preview.mp3 exists (call DownloadPreview if not), then call Python `/shift` on preview.mp3
- [ ] Validate semitones range (-5 to +5)
- [ ] Manual test: preview-shift through several semitones, verify ~1-2s response

## Group 6 — Python Audio Pipeline (heavy endpoints)
Foundation, deps, and JSON logging already done in Group 3.
- [ ] `pitch_service.py` — librosa + pyrubberband + ffmpeg → 128kbps MP3 (shared for preview and full song)
- [ ] `demucs_service.py` — `--two-stems vocals` → vocals.wav + no_vocals.wav
- [ ] `melody_service.py` — CREPE on **vocals.wav** (isolated), outputs melody.json (array tuple format, 30ms hop, min_hz/max_hz, original key)
- [ ] `POST /shift` endpoint — input_path + semitones + output_path; idempotent if output exists
- [ ] `POST /separate` endpoint — input_path + output_dir; idempotent
- [ ] `POST /melody` endpoint — vocals_path + output_path; idempotent
- [ ] Stage timing logs via python-json-logger
- [ ] Manual test: shift a 30s clip, then run separate + melody on a full song, verify outputs

## Group 7 — Generate Pipeline + SSE + Stem Cache
- [ ] `ProcessorClient` in Go: `Shift(in, semitones, out)`, `Separate(in, outDir)`, `Melody(vocals, out)` methods
- [ ] Worker pool with bounded concurrency (env `MAX_CONCURRENT_JOBS=1`)
- [ ] `POST /api/generate` { video_id, semitones } handler:
  - Returns immediately with job_id
  - Goroutine runs pipeline with smart caching: skip yt-dlp full / Demucs / CREPE / shift / transcode if cached
- [ ] SSE `GET /api/status/:jobId` with queue_position
- [ ] `GET /api/audio/:videoId/:semitones` — MP3 via http.ServeFile (Range support)
- [ ] `GET /api/melody/:videoId/:semitones` — server transposes cached original melody by semitones
- [ ] End-to-end test: cold generate (90-180s) → repeat (instant) → same video new semitones (5-15s)

## Group 8 — Vue Frontend (Search + Player)
- [ ] Create Vue 3 project (`npm create vue@latest` — TypeScript, Router, Pinia)
- [ ] Install: Tailwind CSS, **pitchy** (not pitchfinder)
- [ ] Vite proxy config (`/api` → `localhost:8080`)
- [ ] Typed API client (`services/api.ts`)
- [ ] Pinia search store + `SearchView.vue` + `SearchBar.vue` + `SongCard.vue` (click → navigates to player)
- [ ] Pinia player store + `PlayerView.vue`:
  - On mount: fires `/api/preview/:videoId` → plays in original key
  - KeySelector change: fires `/api/preview-shift` → audio reloads
  - "Generate Full Song" button: fires `/api/generate` → progress → full audio plays
- [ ] `KeySelector.vue` — semitone picker (-5 to +5)
- [ ] `AudioPlayer.vue` — `<audio>` wrapper, src swaps between preview and full track
- [ ] `ProcessingStatus.vue` — SSE progress for `/api/generate`
- [ ] `useSSE.ts` with reconnect + polling fallback
- [ ] "Start Singing" enabled only after `/api/generate` done (need melody.json)

## Group 9 — Pitch Detection
- [ ] `usePitchDetection.ts` composable — AudioWorklet + **pitchy (McLeod method)**
- [ ] Pinia pitch store (`stores/pitch.ts`)
- [ ] `PitchMeter.vue` — current note name + cents off
- [ ] `PitchDiagram.vue` — scrolling SVG: blue target line + colored user dot
- [ ] Integrate melody.json: compare live pitch using **`audio.currentTime`** (not performance.now)
- [ ] One-time headphones tooltip on mic permission prompt
- [ ] End-to-end test: sing into mic, verify diagram + feedback
