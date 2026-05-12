package hub

import (
	"context"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"linkup/chat-ws/internal/config"
	"linkup/chat-ws/internal/testutil"
)

func TestFlushDueLastSeen_PatchesBackend(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	var patchCalled atomic.Int32
	var receivedAuth string
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		patchCalled.Add(1)
		receivedAuth = r.Header.Get("Authorization")
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	cfg := config.Config{BackendURL: backend.URL}

	// Schedule debounce, then expire the debounce key (simulating the 10s window passing).
	h.ScheduleLastSeenDebounce(ctx, "user-1", "my-jwt-token")
	s.Del("debounce:last_seen:user-1")

	h.flushDueLastSeen(ctx, cfg)

	assert.Equal(t, int32(1), patchCalled.Load())
	assert.Equal(t, "Bearer my-jwt-token", receivedAuth)
}

func TestFlushDueLastSeen_SkipsIfDebounceAlive(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	var patchCalled atomic.Int32
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		patchCalled.Add(1)
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	cfg := config.Config{BackendURL: backend.URL}

	// Debounce key still alive -- should NOT trigger PATCH.
	h.ScheduleLastSeenDebounce(ctx, "user-1", "token")

	h.flushDueLastSeen(ctx, cfg)

	assert.Equal(t, int32(0), patchCalled.Load())
}

func TestFlushDueLastSeen_CleansUpAfterPatch(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	cfg := config.Config{BackendURL: backend.URL}

	h.ScheduleLastSeenDebounce(ctx, "user-1", "token")
	s.Del("debounce:last_seen:user-1")

	h.flushDueLastSeen(ctx, cfg)

	assert.False(t, s.Exists("last_seen:hold:user-1"), "hold key should be deleted after successful PATCH")
	assert.False(t, s.Exists("last_seen:token:user-1"), "token key should be deleted after successful PATCH")
}

func TestFlushDueLastSeen_KeepsOnBackendFailure(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer backend.Close()

	cfg := config.Config{BackendURL: backend.URL}

	h.ScheduleLastSeenDebounce(ctx, "user-1", "token")
	s.Del("debounce:last_seen:user-1")

	h.flushDueLastSeen(ctx, cfg)

	assert.True(t, s.Exists("last_seen:hold:user-1"), "hold key should remain when backend fails")
}

func TestRunLastSeenDebounceWorker_ExitsOnCancel(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	h := NewHub(client)

	ctx, cancel := context.WithCancel(context.Background())
	cfg := config.Config{BackendURL: "http://localhost:9999"}

	done := make(chan struct{})
	go func() {
		h.RunLastSeenDebounceWorker(ctx, cfg)
		close(done)
	}()

	cancel()

	select {
	case <-done:
		// Exited cleanly.
	case <-time.After(3 * time.Second):
		t.Fatal("RunLastSeenDebounceWorker did not exit on context cancel")
	}
}

func TestFlushDueLastSeen_NilRedis(t *testing.T) {
	h := NewHub(nil)
	cfg := config.Config{BackendURL: "http://localhost:9999"}
	// Should be a no-op, not panic.
	h.flushDueLastSeen(context.Background(), cfg)
}

func TestFlushDueLastSeen_UsesTokenKey(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	var receivedAuth string
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedAuth = r.Header.Get("Authorization")
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	cfg := config.Config{BackendURL: backend.URL}

	h.ScheduleLastSeenDebounce(ctx, "user-1", "original-token")
	s.Del("debounce:last_seen:user-1")

	h.flushDueLastSeen(ctx, cfg)

	require.Equal(t, "Bearer original-token", receivedAuth)
}
