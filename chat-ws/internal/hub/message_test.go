package hub

import (
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestChatMessage_JSON_Roundtrip(t *testing.T) {
	msg := ChatMessage{
		MessageID:      42,
		ConversationID: "conv-1",
		SenderID:       "user-a",
		RecipientID:    "user-b",
		Body:           "hello",
		CreatedAt:      "2026-05-12T08:00:00Z",
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	// Verify JSON field names match the Python backend contract.
	var raw map[string]any
	require.NoError(t, json.Unmarshal(data, &raw))
	assert.Contains(t, raw, "message_id")
	assert.Contains(t, raw, "conversation_id")
	assert.Contains(t, raw, "sender_id")
	assert.Contains(t, raw, "recipient_id")
	assert.Contains(t, raw, "body")
	assert.Contains(t, raw, "created_at")

	var decoded ChatMessage
	require.NoError(t, json.Unmarshal(data, &decoded))
	assert.Equal(t, msg, decoded)
}

func TestTypingPayload_JSON_Roundtrip(t *testing.T) {
	tp := TypingPayload{
		Type:           "typing_start",
		UserID:         "user-a",
		ConversationID: "conv-1",
		RecipientID:    "user-b",
		FullName:       "Alice",
	}

	data, err := json.Marshal(tp)
	require.NoError(t, err)

	var decoded TypingPayload
	require.NoError(t, json.Unmarshal(data, &decoded))
	assert.Equal(t, tp, decoded)
}

func TestTypingPayload_OmitsEmptyFullName(t *testing.T) {
	tp := TypingPayload{
		Type:           "typing_start",
		UserID:         "user-a",
		ConversationID: "conv-1",
		RecipientID:    "user-b",
	}

	data, err := json.Marshal(tp)
	require.NoError(t, err)

	var raw map[string]any
	require.NoError(t, json.Unmarshal(data, &raw))
	_, hasFullName := raw["full_name"]
	assert.False(t, hasFullName, "full_name should be omitted when empty")
}
