package hub

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"linkup/chat-ws/internal/testutil"
)

func TestSetPresence(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	h.SetPresence(ctx, "user-1")

	assert.True(t, s.Exists("presence:user-1"))
	ttl := s.TTL("presence:user-1")
	assert.InDelta(t, 60, ttl.Seconds(), 2)
}

func TestRefreshPresence(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	h.SetPresence(ctx, "user-1")

	// Fast-forward time so TTL decreases.
	s.FastForward(30 * time.Second)

	h.RefreshPresence(ctx, "user-1")

	ttl := s.TTL("presence:user-1")
	assert.InDelta(t, 60, ttl.Seconds(), 2)
}

func TestClearPresence(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	h.SetPresence(ctx, "user-1")
	require.True(t, s.Exists("presence:user-1"))

	h.ClearPresence(ctx, "user-1")
	assert.False(t, s.Exists("presence:user-1"))
}

func TestPublishTyping_Channel(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	// PublishTyping should not panic even without subscribers.
	h.PublishTyping(ctx, "conv-42", []byte(`{"type":"typing_start"}`))
}

func TestPublishTyping_NilRedis(t *testing.T) {
	h := NewHub(nil)
	// Should be a no-op.
	h.PublishTyping(context.Background(), "conv-1", []byte(`{}`))
}

func TestScheduleLastSeenDebounce(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	h.ScheduleLastSeenDebounce(ctx, "user-1", "jwt-token-abc")

	assert.True(t, s.Exists("debounce:last_seen:user-1"))
	assert.True(t, s.Exists("last_seen:hold:user-1"))
	assert.True(t, s.Exists("last_seen:token:user-1"))

	val, err := s.Get("last_seen:token:user-1")
	require.NoError(t, err)
	assert.Equal(t, "jwt-token-abc", val)

	debounceTTL := s.TTL("debounce:last_seen:user-1")
	assert.InDelta(t, 10, debounceTTL.Seconds(), 2)

	holdTTL := s.TTL("last_seen:hold:user-1")
	assert.InDelta(t, 25, holdTTL.Seconds(), 2)
}

func TestScheduleLastSeenDebounce_EmptyToken(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)

	h.ScheduleLastSeenDebounce(context.Background(), "user-1", "")

	assert.False(t, s.Exists("debounce:last_seen:user-1"))
}

func TestClearLastSeenDebounce(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	ctx := context.Background()

	h.ScheduleLastSeenDebounce(ctx, "user-1", "token")
	require.True(t, s.Exists("debounce:last_seen:user-1"))

	h.ClearLastSeenDebounce(ctx, "user-1")

	assert.False(t, s.Exists("debounce:last_seen:user-1"))
	assert.False(t, s.Exists("last_seen:hold:user-1"))
	assert.False(t, s.Exists("last_seen:token:user-1"))
}
