package testutil

import (
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/golang-jwt/jwt/v5"
	"github.com/redis/go-redis/v9"

	"linkup/chat-ws/internal/config"
)

// GenerateTestJWT creates a signed JWT with the given userID as `sub`.
func GenerateTestJWT(userID, secret, alg string) string {
	var method jwt.SigningMethod
	switch alg {
	case "HS384":
		method = jwt.SigningMethodHS384
	case "HS512":
		method = jwt.SigningMethodHS512
	default:
		method = jwt.SigningMethodHS256
	}

	claims := jwt.MapClaims{
		"sub": userID,
		"exp": time.Now().Add(time.Hour).Unix(),
		"iat": time.Now().Unix(),
	}
	token := jwt.NewWithClaims(method, claims)
	signed, err := token.SignedString([]byte(secret))
	if err != nil {
		panic("testutil: failed to sign JWT: " + err.Error())
	}
	return signed
}

// GenerateExpiredJWT creates a signed JWT that has already expired.
func GenerateExpiredJWT(userID, secret, alg string) string {
	claims := jwt.MapClaims{
		"sub": userID,
		"exp": time.Now().Add(-time.Hour).Unix(),
		"iat": time.Now().Add(-2 * time.Hour).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString([]byte(secret))
	if err != nil {
		panic("testutil: failed to sign expired JWT: " + err.Error())
	}
	return signed
}

// MustMiniRedis starts an in-process Redis server and returns the server
// and a connected go-redis client. Both are cleaned up when t finishes.
func MustMiniRedis(t *testing.T) (*miniredis.Miniredis, *redis.Client) {
	t.Helper()
	s, err := miniredis.Run()
	if err != nil {
		t.Fatalf("miniredis.Run: %v", err)
	}
	t.Cleanup(s.Close)

	client := redis.NewClient(&redis.Options{Addr: s.Addr()})
	t.Cleanup(func() { client.Close() })

	return s, client
}

// MustMiniRedisClient creates an additional go-redis client connected to an
// existing miniredis server. Useful when you need separate clients for pub/sub.
func MustMiniRedisClient(t *testing.T, s *miniredis.Miniredis) *redis.Client {
	t.Helper()
	client := redis.NewClient(&redis.Options{Addr: s.Addr()})
	t.Cleanup(func() { client.Close() })
	return client
}

// TestConfig returns a config.Config with test-friendly defaults.
func TestConfig(secret, backendURL string) config.Config {
	if secret == "" {
		secret = "test-secret-key-for-unit-tests"
	}
	if backendURL == "" {
		backendURL = "http://localhost:9999"
	}
	return config.Config{
		Port:       8081,
		SecretKey:  secret,
		JWTAlg:     "HS256",
		BackendURL: backendURL,
	}
}

const (
	TestSecret = "test-secret-key-for-unit-tests"
	TestUserID = "550e8400-e29b-41d4-a716-446655440000"
)
