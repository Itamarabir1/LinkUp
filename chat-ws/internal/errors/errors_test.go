package errors

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestAppError_Error_WithWrapped(t *testing.T) {
	inner := fmt.Errorf("connection refused")
	ae := New("CODE", "something broke", 500, inner)
	assert.Contains(t, ae.Error(), "something broke")
	assert.Contains(t, ae.Error(), "connection refused")
}

func TestAppError_Error_WithoutWrapped(t *testing.T) {
	ae := New("CODE", "plain error", 400, nil)
	assert.Equal(t, "plain error", ae.Error())
}

func TestAppError_Unwrap(t *testing.T) {
	inner := fmt.Errorf("root cause")
	ae := &AppError{Code: "X", Message: "msg", HTTPStatus: 500, Err: inner}
	assert.Equal(t, inner, ae.Unwrap())
}

func TestAppError_Unwrap_Nil(t *testing.T) {
	ae := &AppError{Code: "X", Message: "msg", HTTPStatus: 500, Err: nil}
	assert.Nil(t, ae.Unwrap())
}

func TestWrap(t *testing.T) {
	inner := fmt.Errorf("disk full")
	wrapped := Wrap(inner, "write failed")
	require.Error(t, wrapped)
	assert.Contains(t, wrapped.Error(), "write failed")
	assert.Contains(t, wrapped.Error(), "disk full")
}

func TestWrap_Nil(t *testing.T) {
	assert.Nil(t, Wrap(nil, "should not wrap"))
}

func TestIs_Sentinels(t *testing.T) {
	wrapped := fmt.Errorf("context: %w", ErrAuth)
	assert.True(t, Is(wrapped, ErrAuth))
	assert.False(t, Is(wrapped, ErrConnection))
}
