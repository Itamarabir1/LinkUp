package hub

import (
	"encoding/json"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// newTestConn creates a Conn suitable for in-memory tests (no real websocket).
func newTestConn(userID string) *Conn {
	return &Conn{
		UserID: userID,
		Send:   make(chan []byte, 256),
		done:   make(chan struct{}),
	}
}

func TestRegister_SingleConn(t *testing.T) {
	h := NewHub(nil)
	c := newTestConn("user-1")
	h.Register("user-1", c)

	h.mu.RLock()
	defer h.mu.RUnlock()
	assert.Len(t, h.users["user-1"], 1)
	assert.Same(t, c, h.users["user-1"][0])
}

func TestRegister_MultiDevice(t *testing.T) {
	h := NewHub(nil)
	c1 := newTestConn("user-1")
	c2 := newTestConn("user-1")
	h.Register("user-1", c1)
	h.Register("user-1", c2)

	h.mu.RLock()
	defer h.mu.RUnlock()
	assert.Len(t, h.users["user-1"], 2)
}

func TestUnregister_RemovesConn(t *testing.T) {
	h := NewHub(nil)
	c1 := newTestConn("user-1")
	c2 := newTestConn("user-1")
	h.Register("user-1", c1)
	h.Register("user-1", c2)

	h.Unregister("user-1", c1)

	h.mu.RLock()
	defer h.mu.RUnlock()
	assert.Len(t, h.users["user-1"], 1)
	assert.Same(t, c2, h.users["user-1"][0])
}

func TestUnregister_LastConn_DeletesKey(t *testing.T) {
	h := NewHub(nil)
	c := newTestConn("user-1")
	h.Register("user-1", c)
	h.Unregister("user-1", c)

	h.mu.RLock()
	defer h.mu.RUnlock()
	_, exists := h.users["user-1"]
	assert.False(t, exists, "user key should be deleted when last conn is removed")
}

func TestUnregister_UnknownUser(t *testing.T) {
	h := NewHub(nil)
	c := newTestConn("user-1")
	// Should not panic.
	h.Unregister("unknown", c)
}

func TestSendToUser_Delivers(t *testing.T) {
	h := NewHub(nil)
	c := newTestConn("user-1")
	h.Register("user-1", c)

	payload := []byte(`{"msg":"hello"}`)
	h.SendToUser("user-1", payload)

	select {
	case got := <-c.Send:
		assert.Equal(t, payload, got)
	case <-time.After(time.Second):
		t.Fatal("timed out waiting for message")
	}
}

func TestSendToUser_MultiDevice(t *testing.T) {
	h := NewHub(nil)
	c1 := newTestConn("user-1")
	c2 := newTestConn("user-1")
	h.Register("user-1", c1)
	h.Register("user-1", c2)

	payload := []byte(`{"msg":"hello"}`)
	h.SendToUser("user-1", payload)

	for _, c := range []*Conn{c1, c2} {
		select {
		case got := <-c.Send:
			assert.Equal(t, payload, got)
		case <-time.After(time.Second):
			t.Fatal("timed out waiting for message on conn")
		}
	}
}

func TestSendToUser_UnknownUser(t *testing.T) {
	h := NewHub(nil)
	// Should not panic.
	h.SendToUser("nonexistent", []byte(`{}`))
}

func TestSendToUser_FullChannel(t *testing.T) {
	h := NewHub(nil)
	c := &Conn{
		UserID: "user-1",
		Send:   make(chan []byte, 1), // tiny buffer
		done:   make(chan struct{}),
	}
	h.Register("user-1", c)

	// Fill the channel.
	c.Send <- []byte("first")

	// This should not block (non-blocking select in SendToUser).
	done := make(chan struct{})
	go func() {
		h.SendToUser("user-1", []byte("second"))
		close(done)
	}()

	select {
	case <-done:
		// Good -- didn't deadlock.
	case <-time.After(time.Second):
		t.Fatal("SendToUser blocked on full channel")
	}
}

func TestPublishChatMessage_Routes(t *testing.T) {
	h := NewHub(nil)
	c := newTestConn("recipient-123")
	h.Register("recipient-123", c)

	msg := ChatMessage{
		MessageID:   1,
		RecipientID: "recipient-123",
		SenderID:    "sender-456",
		Body:        "hey",
	}
	payload, err := json.Marshal(msg)
	require.NoError(t, err)

	h.PublishChatMessage(payload)

	select {
	case got := <-c.Send:
		assert.Equal(t, payload, got)
	case <-time.After(time.Second):
		t.Fatal("timed out waiting for chat message")
	}
}

func TestPublishChatMessage_InvalidJSON(t *testing.T) {
	h := NewHub(nil)
	// Should not panic on garbage JSON.
	h.PublishChatMessage([]byte("not json"))
}

func TestPublishTypingMessage_Routes(t *testing.T) {
	h := NewHub(nil)
	c := newTestConn("recipient-123")
	h.Register("recipient-123", c)

	tp := TypingPayload{
		Type:           "typing_start",
		UserID:         "sender-456",
		ConversationID: "conv-1",
		RecipientID:    "recipient-123",
	}
	payload, err := json.Marshal(tp)
	require.NoError(t, err)

	h.PublishTypingMessage(payload)

	select {
	case got := <-c.Send:
		assert.Equal(t, payload, got)
	case <-time.After(time.Second):
		t.Fatal("timed out waiting for typing message")
	}
}

func TestPublishTypingMessage_InvalidJSON(t *testing.T) {
	h := NewHub(nil)
	h.PublishTypingMessage([]byte("{invalid"))
}

func TestBroadcastOnline(t *testing.T) {
	h := NewHub(nil)
	c1 := newTestConn("user-a")
	c2 := newTestConn("user-b")
	c3 := newTestConn("user-a") // second device for user-a
	h.Register("user-a", c1)
	h.Register("user-b", c2)
	h.Register("user-a", c3)

	h.broadcastOnline("user-x")

	for _, c := range []*Conn{c1, c2, c3} {
		select {
		case got := <-c.Send:
			var ev map[string]string
			require.NoError(t, json.Unmarshal(got, &ev))
			assert.Equal(t, "user_online", ev["type"])
			assert.Equal(t, "user-x", ev["user_id"])
		case <-time.After(time.Second):
			t.Fatal("timed out waiting for broadcast")
		}
	}
}

func TestBroadcastOffline(t *testing.T) {
	h := NewHub(nil)
	c1 := newTestConn("user-a")
	c2 := newTestConn("user-b")
	h.Register("user-a", c1)
	h.Register("user-b", c2)

	h.broadcastOffline("user-x")

	for _, c := range []*Conn{c1, c2} {
		select {
		case got := <-c.Send:
			var ev map[string]string
			require.NoError(t, json.Unmarshal(got, &ev))
			assert.Equal(t, "user_offline", ev["type"])
			assert.Equal(t, "user-x", ev["user_id"])
		case <-time.After(time.Second):
			t.Fatal("timed out waiting for broadcast")
		}
	}
}

func TestMarkSubAlive_SubscribersHealthy(t *testing.T) {
	h := NewHub(nil)

	// Freshly created hub should be healthy (seeded in NewHub).
	assert.True(t, h.SubscribersHealthy())

	// Mark one subscriber as stale.
	h.chatSubAt.Store(time.Now().Add(-3 * time.Minute).UnixMilli())
	assert.False(t, h.SubscribersHealthy())

	// Mark it alive again.
	h.MarkSubAlive(SubChat)
	assert.True(t, h.SubscribersHealthy())
}

func TestConcurrentRegisterUnregister(t *testing.T) {
	h := NewHub(nil)
	var wg sync.WaitGroup
	const n = 100

	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			c := newTestConn("user-1")
			h.Register("user-1", c)
			h.SendToUser("user-1", []byte("ping"))
			h.Unregister("user-1", c)
		}()
	}
	wg.Wait()
}
