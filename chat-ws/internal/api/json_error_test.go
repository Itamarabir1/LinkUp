package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestWriteAPIError_Format(t *testing.T) {
	w := httptest.NewRecorder()
	r := httptest.NewRequest(http.MethodGet, "/test", nil)

	WriteAPIError(w, r, http.StatusBadRequest, "BAD_INPUT", "invalid field")

	assert.Equal(t, http.StatusBadRequest, w.Code)
	assert.Contains(t, w.Header().Get("Content-Type"), "application/json")

	var body map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.Equal(t, "error", body["status"])
	assert.Equal(t, "BAD_INPUT", body["error_code"])
	assert.Equal(t, "invalid field", body["message"])
	assert.NotEmpty(t, body["trace_id"])
}

func TestWriteAPIError_StatusCode(t *testing.T) {
	tests := []struct {
		code int
	}{
		{http.StatusUnauthorized},
		{http.StatusForbidden},
		{http.StatusInternalServerError},
	}
	for _, tt := range tests {
		w := httptest.NewRecorder()
		WriteAPIError(w, httptest.NewRequest(http.MethodGet, "/", nil), tt.code, "ERR", "msg")
		assert.Equal(t, tt.code, w.Code)
	}
}

func TestWriteAPIError_UsesRequestID(t *testing.T) {
	w := httptest.NewRecorder()
	r := httptest.NewRequest(http.MethodGet, "/test", nil)
	r.Header.Set("X-Request-ID", "req-abc-123")

	WriteAPIError(w, r, http.StatusOK, "OK", "ok")

	var body map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.Equal(t, "req-abc-123", body["trace_id"])
}

func TestWriteAPIError_GeneratesTraceID(t *testing.T) {
	w := httptest.NewRecorder()
	r := httptest.NewRequest(http.MethodGet, "/test", nil)

	WriteAPIError(w, r, http.StatusOK, "OK", "ok")

	var body map[string]any
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	traceID, ok := body["trace_id"].(string)
	require.True(t, ok)
	assert.Len(t, traceID, 8) // 4 random bytes -> 8 hex chars
}
