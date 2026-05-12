package main

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestParseRedisURL_WithPassword(t *testing.T) {
	password, db, err := parseRedisURL("redis://:mypass@host:6379/2")
	require.NoError(t, err)
	assert.Equal(t, "mypass", password)
	assert.Equal(t, 2, db)
}

func TestParseRedisURL_NoPassword(t *testing.T) {
	password, db, err := parseRedisURL("redis://host:6379/1")
	require.NoError(t, err)
	assert.Equal(t, "", password)
	assert.Equal(t, 1, db)
}

func TestParseRedisURL_NoDB(t *testing.T) {
	password, db, err := parseRedisURL("redis://host:6379")
	require.NoError(t, err)
	assert.Equal(t, "", password)
	assert.Equal(t, 0, db)
}

func TestParseRedisURL_DefaultURL(t *testing.T) {
	password, db, err := parseRedisURL("redis://localhost:6379/1")
	require.NoError(t, err)
	assert.Equal(t, "", password)
	assert.Equal(t, 1, db)
}

func TestParseRedisURL_Invalid(t *testing.T) {
	_, _, err := parseRedisURL("redis://host:6379/notanumber")
	require.Error(t, err)
}
