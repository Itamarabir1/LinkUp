package redis

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"linkup/chat-ws/internal/hub"
	"linkup/chat-ws/internal/testutil"
)

// newTestConn creates a hub.Conn suitable for tests (no real websocket).
func newTestConn(userID string) *hub.Conn {
	return &hub.Conn{
		UserID: userID,
		Send:   make(chan []byte, 256),
	}
}

func TestRunOnce_ChatMessage(t *testing.T) {
	s, _ := testutil.MustMiniRedis(t)
	h := hub.NewHub(nil)

	recipientConn := newTestConn("recipient-1")
	h.Register("recipient-1", recipientConn)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Start subscriber in a goroutine -- needs a separate client for PSubscribe.
	subClient := testutil.MustMiniRedisClient(t, s)
	go runOnce(ctx, subClient, h)

	// Wait for subscription to be established.
	time.Sleep(100 * time.Millisecond)

	msg := hub.ChatMessage{
		MessageID:      1,
		ConversationID: "conv-1",
		SenderID:       "sender-1",
		RecipientID:    "recipient-1",
		Body:           "hello from test",
	}
	payload, err := json.Marshal(msg)
	require.NoError(t, err)

	s.Publish("chat:conversation:conv-1", string(payload))

	select {
	case got := <-recipientConn.Send:
		var received hub.ChatMessage
		require.NoError(t, json.Unmarshal(got, &received))
		assert.Equal(t, "hello from test", received.Body)
		assert.Equal(t, "recipient-1", received.RecipientID)
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for chat message dispatch")
	}
}

func TestRunOnce_TypingEvent(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	_ = client
	h := hub.NewHub(nil)

	recipientConn := newTestConn("recipient-1")
	h.Register("recipient-1", recipientConn)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	subClient := testutil.MustMiniRedisClient(t, s)
	go runOnce(ctx, subClient, h)

	time.Sleep(100 * time.Millisecond)

	tp := hub.TypingPayload{
		Type:           "typing_start",
		UserID:         "sender-1",
		ConversationID: "conv-1",
		RecipientID:    "recipient-1",
	}
	payload, err := json.Marshal(tp)
	require.NoError(t, err)

	s.Publish("chat:typing:conv-1", string(payload))

	select {
	case got := <-recipientConn.Send:
		var received hub.TypingPayload
		require.NoError(t, json.Unmarshal(got, &received))
		assert.Equal(t, "typing_start", received.Type)
		assert.Equal(t, "recipient-1", received.RecipientID)
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for typing event dispatch")
	}
}

func TestRunOnce_UserEvent(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	_ = client
	h := hub.NewHub(nil)

	userConn := newTestConn("user-42")
	h.Register("user-42", userConn)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	subClient := testutil.MustMiniRedisClient(t, s)
	go runOnce(ctx, subClient, h)

	time.Sleep(100 * time.Millisecond)

	eventPayload := `{"type":"new_notification","data":"test"}`
	s.Publish("user:user-42:events", eventPayload)

	select {
	case got := <-userConn.Send:
		assert.Equal(t, eventPayload, string(got))
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for user event dispatch")
	}
}

func TestRunOnce_ContextCancel(t *testing.T) {
	s, _ := testutil.MustMiniRedis(t)
	h := hub.NewHub(nil)

	ctx, cancel := context.WithCancel(context.Background())

	subClient := testutil.MustMiniRedisClient(t, s)

	done := make(chan struct{})
	go func() {
		runOnce(ctx, subClient, h)
		close(done)
	}()

	time.Sleep(50 * time.Millisecond)
	cancel()

	select {
	case <-done:
		// Exited cleanly.
	case <-time.After(2 * time.Second):
		t.Fatal("runOnce did not exit on context cancel")
	}
}

func TestRunSubscriber_ExitsOnCancel(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	h := hub.NewHub(nil)

	ctx, cancel := context.WithCancel(context.Background())

	done := make(chan struct{})
	go func() {
		RunSubscriber(ctx, client, h)
		close(done)
	}()

	time.Sleep(50 * time.Millisecond)
	cancel()

	select {
	case <-done:
		// Exited cleanly.
	case <-time.After(3 * time.Second):
		t.Fatal("RunSubscriber did not exit on context cancel")
	}
}
