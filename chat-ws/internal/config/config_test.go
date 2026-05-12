package config

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func setEnvs(t *testing.T, envs map[string]string) {
	for k, v := range envs {
		t.Setenv(k, v)
	}
}

func TestLoadConfig_Defaults(t *testing.T) {
	// Clear any env vars that would affect defaults.
	for _, k := range []string{"PORT", "REDIS_URL", "REDIS_ADDR", "SECRET_KEY", "JWT_SECRET",
		"JWT_ALGORITHM", "BACKEND_URL", "ALLOWED_ORIGINS", "REDIS_SENTINEL_ADDR", "REDIS_MASTER_NAME"} {
		t.Setenv(k, "")
	}

	cfg := LoadConfig()
	assert.Equal(t, 8081, cfg.Port)
	assert.Equal(t, "redis://localhost:6379/1", cfg.RedisURL)
	assert.Equal(t, "redis:6379", cfg.RedisAddr)
	assert.Equal(t, "HS256", cfg.JWTAlg)
	assert.Equal(t, "http://localhost:8000", cfg.BackendURL)
	assert.False(t, cfg.UseSentinel)
	assert.Empty(t, cfg.AllowedOrigins)
}

func TestLoadConfig_EnvOverrides(t *testing.T) {
	setEnvs(t, map[string]string{
		"PORT":         "9090",
		"REDIS_URL":    "redis://myhost:6380/3",
		"REDIS_ADDR":   "myhost:6380",
		"SECRET_KEY":   "my-secret",
		"JWT_ALGORITHM": "HS512",
		"BACKEND_URL":  "http://backend:3000",
	})

	cfg := LoadConfig()
	assert.Equal(t, 9090, cfg.Port)
	assert.Equal(t, "redis://myhost:6380/3", cfg.RedisURL)
	assert.Equal(t, "myhost:6380", cfg.RedisAddr)
	assert.Equal(t, "my-secret", cfg.SecretKey)
	assert.Equal(t, "HS512", cfg.JWTAlg)
	assert.Equal(t, "http://backend:3000", cfg.BackendURL)
}

func TestLoadConfig_JWTSecret_Fallback(t *testing.T) {
	t.Setenv("SECRET_KEY", "")
	t.Setenv("JWT_SECRET", "fallback-secret")
	cfg := LoadConfig()
	assert.Equal(t, "fallback-secret", cfg.SecretKey)
}

func TestLoadConfig_AllowedOrigins(t *testing.T) {
	t.Setenv("ALLOWED_ORIGINS", " http://a.com , http://b.com , http://c.com ")
	cfg := LoadConfig()
	assert.Equal(t, []string{"http://a.com", "http://b.com", "http://c.com"}, cfg.AllowedOrigins)
}

func TestLoadConfig_AllowedOrigins_Empty(t *testing.T) {
	t.Setenv("ALLOWED_ORIGINS", "")
	cfg := LoadConfig()
	assert.Empty(t, cfg.AllowedOrigins)
}

func TestLoadConfig_Sentinel(t *testing.T) {
	t.Setenv("REDIS_SENTINEL_ADDR", "sentinel:26379")
	t.Setenv("REDIS_MASTER_NAME", "leader")
	cfg := LoadConfig()
	assert.True(t, cfg.UseSentinel)
	assert.Equal(t, "sentinel:26379", cfg.RedisSentinelAddr)
	assert.Equal(t, "leader", cfg.RedisMasterName)
}
