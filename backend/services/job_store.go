package services

import (
	"context"
	"sync"
	"time"

	"cantus/backend/models"
)

// JobStore is a thread-safe, TTL-based in-memory store for Job records.
type JobStore struct {
	mu   sync.RWMutex
	jobs map[string]models.Job
	ttl  time.Duration
}

// NewJobStore returns a JobStore with the given record TTL.
func NewJobStore(ttl time.Duration) *JobStore {
	return &JobStore{
		jobs: make(map[string]models.Job),
		ttl:  ttl,
	}
}

// Create stores job under job.ID, overwriting any existing entry.
func (s *JobStore) Create(job models.Job) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.jobs[job.ID] = job
}

// Get returns the job for the given id and true, or the zero value and false.
func (s *JobStore) Get(id string) (models.Job, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	j, ok := s.jobs[id]
	return j, ok
}

// Update runs fn against the job identified by id and persists the result.
// Returns false (without calling fn) if id is not present.
func (s *JobStore) Update(id string, fn func(*models.Job)) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	j, ok := s.jobs[id]
	if !ok {
		return false
	}
	fn(&j)
	s.jobs[id] = j
	return true
}

// Delete removes the job with the given id. Safe to call for missing ids.
func (s *JobStore) Delete(id string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.jobs, id)
}

// Cleanup removes all jobs whose CreatedAt is older than the store TTL.
// Returns the number of records evicted.
func (s *JobStore) Cleanup() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	evicted := 0
	for id, j := range s.jobs {
		if time.Since(j.CreatedAt) > s.ttl {
			delete(s.jobs, id)
			evicted++
		}
	}
	return evicted
}

// StartCleanup launches a background goroutine that calls Cleanup every interval.
// The goroutine exits when ctx is cancelled.
func (s *JobStore) StartCleanup(ctx context.Context, interval time.Duration) {
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				s.Cleanup()
			}
		}
	}()
}
