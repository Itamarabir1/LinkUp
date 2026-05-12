package auth

import (
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const testSecret = "test-secret-key"

func signJWT(sub, secret string, method jwt.SigningMethod, exp time.Time) string {
	claims := jwt.MapClaims{"sub": sub, "exp": exp.Unix(), "iat": time.Now().Unix()}
	token := jwt.NewWithClaims(method, claims)
	s, err := token.SignedString([]byte(secret))
	if err != nil {
		panic(err)
	}
	return s
}

func TestValidateToken_Valid(t *testing.T) {
	token := signJWT("550e8400-e29b-41d4-a716-446655440000", testSecret, jwt.SigningMethodHS256, time.Now().Add(time.Hour))
	userID, err := ValidateToken(token, testSecret, "HS256")
	require.NoError(t, err)
	assert.Equal(t, "550e8400-e29b-41d4-a716-446655440000", userID)
}

func TestValidateToken_EmptySecret(t *testing.T) {
	_, err := ValidateToken("some.token.here", "", "HS256")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "SECRET_KEY is required")
}

func TestValidateToken_WrongAlg(t *testing.T) {
	token := signJWT("user1", testSecret, jwt.SigningMethodHS384, time.Now().Add(time.Hour))
	_, err := ValidateToken(token, testSecret, "HS256")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "unexpected alg")
}

func TestValidateToken_ExpiredToken(t *testing.T) {
	token := signJWT("user1", testSecret, jwt.SigningMethodHS256, time.Now().Add(-time.Hour))
	_, err := ValidateToken(token, testSecret, "HS256")
	require.Error(t, err)
}

func TestValidateToken_EmptySub(t *testing.T) {
	token := signJWT("", testSecret, jwt.SigningMethodHS256, time.Now().Add(time.Hour))
	_, err := ValidateToken(token, testSecret, "HS256")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "empty sub")
}

func TestValidateToken_Malformed(t *testing.T) {
	_, err := ValidateToken("not-a-jwt", testSecret, "HS256")
	require.Error(t, err)
}
