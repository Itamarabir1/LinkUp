package config

import (
	"os"
	"strconv"
	"strings"
)

// Config holds env-based configuration. Same SECRET_KEY and REDIS_URL as Python backend.
type Config struct {
	Port            int      // WS server port (default 8081)
	RedisURL        string   // e.g. redis://localhost:6379/0
	SecretKey       string   // JWT secret (same as Python SECRET_KEY)
	JWTAlg          string   // HS256
	BackendURL      string   // e.g. http://localhost:8000
	AllowedOrigins  []string // from ALLOWED_ORIGINS (comma-separated); empty = allow any origin (dev)
}

func LoadConfig() Config {
	port := 8081
	if p := os.Getenv("PORT"); p != "" {
		if v, err := strconv.Atoi(p); err == nil {
			port = v
		}
	}
	redisURL := os.Getenv("REDIS_URL")
	// ברירת מחדל DB=1 — תואם ל-backend REDIS_CHAT_DB (הודעות + chat-ws באותו DB)
	if redisURL == "" {
		redisURL = "redis://localhost:6379/1"
	}
	secret := os.Getenv("SECRET_KEY")
	if secret == "" {
		secret = os.Getenv("JWT_SECRET")
	}
	alg := os.Getenv("JWT_ALGORITHM")
	if alg == "" {
		alg = "HS256"
	}
	backendURL := os.Getenv("BACKEND_URL")
	if backendURL == "" {
		backendURL = "http://localhost:8000"
	}
	var allowedOrigins []string
	if raw := strings.TrimSpace(os.Getenv("ALLOWED_ORIGINS")); raw != "" {
		for _, p := range strings.Split(raw, ",") {
			if o := strings.TrimSpace(p); o != "" {
				allowedOrigins = append(allowedOrigins, o)
			}
		}
	}
	return Config{
		Port:           port,
		RedisURL:       redisURL,
		SecretKey:      secret,
		JWTAlg:         alg,
		BackendURL:     backendURL,
		AllowedOrigins: allowedOrigins,
	}
}
