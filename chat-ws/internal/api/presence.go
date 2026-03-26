package api

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	redisv9 "github.com/redis/go-redis/v9"

	"linkup/chat-ws/internal/auth"
	"linkup/chat-ws/internal/config"
)

const (
	lastSeenHoldKeyPrefix = "last_seen:hold:"
)

type presenceResponse struct {
	Online   bool    `json:"online"`
	LastSeen *string `json:"last_seen"`
}

type lastSeenBackendBody struct {
	LastSeen *string `json:"last_seen"`
}

// HandlePresence serves GET /presence/{userID}. Online from Redis DB (same as hub).
// last_seen: spec asks hold key first — hold currently stores JWT; if not ISO timestamp, falls back to backend.
func HandlePresence(cfg config.Config, rdb *redisv9.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		allowCORS(cfg, w, r)
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		if r.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		authHeader := strings.TrimSpace(r.Header.Get("Authorization"))
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
			http.Error(w, "missing bearer token", http.StatusUnauthorized)
			return
		}
		token := strings.TrimSpace(parts[1])
		if _, err := auth.ValidateToken(token, cfg.SecretKey, cfg.JWTAlg); err != nil {
			http.Error(w, "invalid token", http.StatusUnauthorized)
			return
		}

		rest := strings.TrimPrefix(r.URL.Path, "/presence/")
		if rest == "" || strings.Contains(rest, "/") {
			http.Error(w, "missing or invalid user id", http.StatusBadRequest)
			return
		}
		userID := rest

		ctx := r.Context()
		n, err := rdb.Exists(ctx, "presence:"+userID).Result()
		if err != nil {
			http.Error(w, "redis error", http.StatusInternalServerError)
			return
		}
		online := n > 0

		var lastSeen *string
		holdVal, _ := rdb.Get(ctx, lastSeenHoldKeyPrefix+userID).Result()
		if holdVal != "" {
			if ts, ok := parseAsLastSeen(holdVal); ok {
				lastSeen = &ts
			}
		}
		if lastSeen == nil {
			ls, err := fetchLastSeenFromBackend(ctx, cfg.BackendURL, userID, authHeader)
			if err == nil {
				lastSeen = ls
			}
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(presenceResponse{
			Online:   online,
			LastSeen: lastSeen,
		})
	}
}

func parseAsLastSeen(s string) (string, bool) {
	s = strings.TrimSpace(s)
	if len(s) < 20 || s[0] != '2' {
		return "", false
	}
	for _, layout := range []string{
		time.RFC3339Nano,
		time.RFC3339,
		"2006-01-02T15:04:05.000000+00:00",
	} {
		if t, err := time.Parse(layout, s); err == nil {
			return t.UTC().Format(time.RFC3339), true
		}
	}
	return "", false
}

func fetchLastSeenFromBackend(ctx context.Context, baseURL, userID, authorization string) (*string, error) {
	url := strings.TrimRight(baseURL, "/") + "/api/v1/users/" + userID + "/last-seen"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", authorization)
	client := &http.Client{Timeout: 8 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("backend %d", resp.StatusCode)
	}
	var out lastSeenBackendBody
	if err := json.Unmarshal(body, &out); err != nil {
		return nil, err
	}
	return out.LastSeen, nil
}

func allowCORS(cfg config.Config, w http.ResponseWriter, r *http.Request) {
	origin := r.Header.Get("Origin")
	if origin != "" {
		allowed := len(cfg.AllowedOrigins) == 0
		if !allowed {
			for _, o := range cfg.AllowedOrigins {
				if o == origin {
					allowed = true
					break
				}
			}
		}
		if allowed {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Credentials", "true")
		}
	} else {
		w.Header().Set("Access-Control-Allow-Origin", "*")
	}
	w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Authorization, Content-Type")
}
