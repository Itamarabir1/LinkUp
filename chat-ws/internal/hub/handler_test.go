package hub

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"linkup/chat-ws/internal/config"
	"linkup/chat-ws/internal/testutil"
)

func wsTestSetup(t *testing.T, cfg config.Config) (*Hub, *httptest.Server) {
	t.Helper()
	_, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	srv := httptest.NewServer(h.HandleWS(cfg))
	t.Cleanup(srv.Close)
	return h, srv
}

func wsURL(srv *httptest.Server, token string) string {
	u := "ws" + strings.TrimPrefix(srv.URL, "http") + "/ws?token=" + token
	return u
}

func dialWS(t *testing.T, url string) *websocket.Conn {
	t.Helper()
	dialer := websocket.Dialer{HandshakeTimeout: 2 * time.Second}
	conn, resp, err := dialer.Dial(url, nil)
	if err != nil {
		if resp != nil {
			t.Fatalf("ws dial failed: %v (status %d)", err, resp.StatusCode)
		}
		t.Fatalf("ws dial failed: %v", err)
	}
	t.Cleanup(func() { conn.Close() })
	return conn
}

func TestHandleWS_NoToken(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	_, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	srv := httptest.NewServer(h.HandleWS(cfg))
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/ws")
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, http.StatusUnauthorized, resp.StatusCode)
}

func TestHandleWS_InvalidToken(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	_, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	srv := httptest.NewServer(h.HandleWS(cfg))
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/ws?token=invalid-jwt")
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, http.StatusUnauthorized, resp.StatusCode)
}

func TestHandleWS_SuccessfulUpgrade(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	h, srv := wsTestSetup(t, cfg)
	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")

	conn := dialWS(t, wsURL(srv, token))
	_ = conn

	// Give the handler goroutine time to register.
	time.Sleep(50 * time.Millisecond)

	h.mu.RLock()
	conns := h.users[testutil.TestUserID]
	h.mu.RUnlock()
	assert.Len(t, conns, 1)
}

func TestHandleWS_PresenceSetOnConnect(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	srv := httptest.NewServer(h.HandleWS(cfg))
	defer srv.Close()

	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")
	conn := dialWS(t, wsURL(srv, token))
	_ = conn

	time.Sleep(50 * time.Millisecond)
	assert.True(t, s.Exists("presence:"+testutil.TestUserID))
}

func TestHandleWS_PingPong(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	_, srv := wsTestSetup(t, cfg)
	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")
	conn := dialWS(t, wsURL(srv, token))

	err := conn.WriteMessage(websocket.TextMessage, []byte(`{"type":"ping"}`))
	require.NoError(t, err)

	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	_, msg, err := conn.ReadMessage()
	require.NoError(t, err)

	var resp map[string]string
	require.NoError(t, json.Unmarshal(msg, &resp))
	assert.Equal(t, "pong", resp["type"])
}

func TestHandleWS_TypingStart(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	_, srv := wsTestSetup(t, cfg)
	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")
	conn := dialWS(t, wsURL(srv, token))

	msg := map[string]string{
		"type":            "typing_start",
		"conversation_id": "conv-1",
		"recipient_id":    "other-user",
		"full_name":       "Test User",
	}
	data, _ := json.Marshal(msg)
	err := conn.WriteMessage(websocket.TextMessage, data)
	require.NoError(t, err)

	// Give handler time to process.
	time.Sleep(100 * time.Millisecond)
}

func TestHandleWS_TypingStop(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	_, srv := wsTestSetup(t, cfg)
	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")
	conn := dialWS(t, wsURL(srv, token))

	msg := map[string]string{
		"type":            "typing_stop",
		"conversation_id": "conv-1",
		"recipient_id":    "other-user",
	}
	data, _ := json.Marshal(msg)
	err := conn.WriteMessage(websocket.TextMessage, data)
	require.NoError(t, err)

	time.Sleep(100 * time.Millisecond)
}

func TestHandleWS_InvalidJSON(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	_, srv := wsTestSetup(t, cfg)
	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")
	conn := dialWS(t, wsURL(srv, token))

	err := conn.WriteMessage(websocket.TextMessage, []byte("not json{"))
	require.NoError(t, err)

	// Server should close the connection with policy violation.
	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	_, _, err = conn.ReadMessage()
	require.Error(t, err)

	var closeErr *websocket.CloseError
	if assert.ErrorAs(t, err, &closeErr) {
		assert.Equal(t, websocket.ClosePolicyViolation, closeErr.Code)
	}
}

func TestHandleWS_Disconnect(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	s, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	srv := httptest.NewServer(h.HandleWS(cfg))
	defer srv.Close()

	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")
	dialer := websocket.Dialer{HandshakeTimeout: 2 * time.Second}
	conn, _, err := dialer.Dial(wsURL(srv, token), nil)
	require.NoError(t, err)

	time.Sleep(50 * time.Millisecond)

	h.mu.RLock()
	assert.Len(t, h.users[testutil.TestUserID], 1)
	h.mu.RUnlock()

	// Close the connection from client side.
	conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
	conn.Close()

	// Wait for server-side cleanup.
	time.Sleep(200 * time.Millisecond)

	h.mu.RLock()
	_, exists := h.users[testutil.TestUserID]
	h.mu.RUnlock()
	assert.False(t, exists, "user should be unregistered after disconnect")
	assert.False(t, s.Exists("presence:"+testutil.TestUserID), "presence should be cleared")
}

func TestHandleWS_OriginCheck_Allowed(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	cfg.AllowedOrigins = []string{"http://allowed.com"}

	_, srv := wsTestSetup(t, cfg)
	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")

	dialer := websocket.Dialer{HandshakeTimeout: 2 * time.Second}
	header := http.Header{}
	header.Set("Origin", "http://allowed.com")
	conn, _, err := dialer.Dial(wsURL(srv, token), header)
	require.NoError(t, err)
	conn.Close()
}

func TestHandleWS_OriginCheck_Blocked(t *testing.T) {
	cfg := testutil.TestConfig("", "")
	cfg.AllowedOrigins = []string{"http://allowed.com"}

	_, client := testutil.MustMiniRedis(t)
	h := NewHub(client)
	srv := httptest.NewServer(h.HandleWS(cfg))
	defer srv.Close()

	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")

	dialer := websocket.Dialer{HandshakeTimeout: 2 * time.Second}
	header := http.Header{}
	header.Set("Origin", "http://evil.com")
	_, _, err := dialer.Dial(wsURL(srv, token), header)
	require.Error(t, err, "should reject non-allowed origin")
}
