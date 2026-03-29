package api

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"strings"
)

// WriteAPIError writes the same error JSON shape as Linkup FastAPI (status, error_code, message, trace_id).
// Uses X-Request-ID from r when present so traces align with callers; otherwise a short random id.
func WriteAPIError(w http.ResponseWriter, r *http.Request, status int, errorCode, message string) {
	tid := ""
	if r != nil {
		tid = strings.TrimSpace(r.Header.Get("X-Request-ID"))
	}
	if tid == "" {
		trace := make([]byte, 4)
		if _, err := rand.Read(trace); err != nil {
			trace = []byte{0, 0, 0, 0}
		}
		tid = hex.EncodeToString(trace)
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"status":     "error",
		"error_code": errorCode,
		"message":    message,
		"trace_id":   tid,
	})
}
