package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"linkup/chat-ws/internal/testutil"
)

func TestHandlePresence_Online(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")

	s.Set("presence:user-1", "1")

	handler := HandlePresence(cfg, client)
	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")

	r := httptest.NewRequest(http.MethodGet, "/presence/user-1", nil)
	r.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	handler(w, r)

	assert.Equal(t, http.StatusOK, w.Code)

	var body presenceResponse
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.True(t, body.Online)
}

func TestHandlePresence_Offline(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")

	handler := HandlePresence(cfg, client)
	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")

	r := httptest.NewRequest(http.MethodGet, "/presence/user-1", nil)
	r.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	handler(w, r)

	assert.Equal(t, http.StatusOK, w.Code)

	var body presenceResponse
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.False(t, body.Online)
}

func TestHandlePresence_LastSeenFromHold(t *testing.T) {
	s, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")

	s.Set("last_seen:hold:user-1", "2026-05-12T08:00:00+00:00")

	handler := HandlePresence(cfg, client)
	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")

	r := httptest.NewRequest(http.MethodGet, "/presence/user-1", nil)
	r.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	handler(w, r)

	var body presenceResponse
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	require.NotNil(t, body.LastSeen)
	assert.Equal(t, "2026-05-12T08:00:00Z", *body.LastSeen)
}

func TestHandlePresence_LastSeenFromBackend(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"last_seen":"2026-01-01T12:00:00Z"}`))
	}))
	defer backend.Close()

	cfg := testutil.TestConfig("", backend.URL)

	handler := HandlePresence(cfg, client)
	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")

	r := httptest.NewRequest(http.MethodGet, "/presence/user-1", nil)
	r.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	handler(w, r)

	var body presenceResponse
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	require.NotNil(t, body.LastSeen)
	assert.Equal(t, "2026-01-01T12:00:00Z", *body.LastSeen)
}

func TestHandlePresence_NoAuth(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")
	handler := HandlePresence(cfg, client)

	r := httptest.NewRequest(http.MethodGet, "/presence/user-1", nil)
	w := httptest.NewRecorder()
	handler(w, r)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestHandlePresence_InvalidToken(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")
	handler := HandlePresence(cfg, client)

	r := httptest.NewRequest(http.MethodGet, "/presence/user-1", nil)
	r.Header.Set("Authorization", "Bearer invalid-jwt-token")
	w := httptest.NewRecorder()
	handler(w, r)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestHandlePresence_CORS_AllowedOrigin(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")
	cfg.AllowedOrigins = []string{"http://app.example.com"}
	handler := HandlePresence(cfg, client)

	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")
	r := httptest.NewRequest(http.MethodGet, "/presence/user-1", nil)
	r.Header.Set("Authorization", "Bearer "+token)
	r.Header.Set("Origin", "http://app.example.com")
	w := httptest.NewRecorder()
	handler(w, r)

	assert.Equal(t, "http://app.example.com", w.Header().Get("Access-Control-Allow-Origin"))
}

func TestHandlePresence_CORS_DisallowedOrigin(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")
	cfg.AllowedOrigins = []string{"http://app.example.com"}
	handler := HandlePresence(cfg, client)

	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")
	r := httptest.NewRequest(http.MethodGet, "/presence/user-1", nil)
	r.Header.Set("Authorization", "Bearer "+token)
	r.Header.Set("Origin", "http://evil.com")
	w := httptest.NewRecorder()
	handler(w, r)

	assert.Empty(t, w.Header().Get("Access-Control-Allow-Origin"))
}

func TestHandlePresence_CORS_NoOrigin(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")
	handler := HandlePresence(cfg, client)

	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")
	r := httptest.NewRequest(http.MethodGet, "/presence/user-1", nil)
	r.Header.Set("Authorization", "Bearer "+token)
	w := httptest.NewRecorder()
	handler(w, r)

	assert.Equal(t, "*", w.Header().Get("Access-Control-Allow-Origin"))
}

func TestHandlePresence_MethodNotAllowed(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")
	handler := HandlePresence(cfg, client)

	r := httptest.NewRequest(http.MethodPost, "/presence/user-1", nil)
	r.Header.Set("Authorization", "Bearer token")
	w := httptest.NewRecorder()
	handler(w, r)

	assert.Equal(t, http.StatusMethodNotAllowed, w.Code)
}

func TestHandlePresence_Options(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")
	handler := HandlePresence(cfg, client)

	r := httptest.NewRequest(http.MethodOptions, "/presence/user-1", nil)
	w := httptest.NewRecorder()
	handler(w, r)

	assert.Equal(t, http.StatusNoContent, w.Code)
}

func TestHandlePresence_BadUserID(t *testing.T) {
	_, client := testutil.MustMiniRedis(t)
	cfg := testutil.TestConfig("", "")
	handler := HandlePresence(cfg, client)

	token := testutil.GenerateTestJWT(testutil.TestUserID, testutil.TestSecret, "HS256")

	tests := []struct {
		path string
	}{
		{"/presence/"},
		{"/presence/user/extra"},
	}
	for _, tt := range tests {
		r := httptest.NewRequest(http.MethodGet, tt.path, nil)
		r.Header.Set("Authorization", "Bearer "+token)
		w := httptest.NewRecorder()
		handler(w, r)
		assert.Equal(t, http.StatusBadRequest, w.Code, "path: %s", tt.path)
	}
}
