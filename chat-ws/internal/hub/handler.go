package hub

import (
	"context"
	"encoding/json"
	"log"
	"net/http"

	"github.com/gorilla/websocket"

	"linkup/chat-ws/internal/auth"
	"linkup/chat-ws/internal/config"
)

// clientIncoming is the shape of JSON sent by the client (e.g. typing_start).
type clientIncoming struct {
	Type           string `json:"type"`
	ConversationID string `json:"conversation_id"`
	RecipientID    string `json:"recipient_id"`
	FullName       string `json:"full_name,omitempty"`
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // allow same-origin or set your frontend origin
	},
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
}

// HandleWS upgrades HTTP to WebSocket. Query: token=JWT. Validates token and registers connection.
func (h *Hub) HandleWS(cfg config.Config) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		token := r.URL.Query().Get("token")
		if token == "" {
			http.Error(w, "missing token", http.StatusUnauthorized)
			return
		}
		userID, err := auth.ValidateToken(token, cfg.SecretKey, cfg.JWTAlg)
		if err != nil {
			http.Error(w, "invalid token", http.StatusUnauthorized)
			return
		}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("ws upgrade: %v", err)
			return
		}
		c := &Conn{UserID: userID, Conn: conn, Send: make(chan []byte, 256)}
		h.Register(userID, c)
		h.SetPresence(context.Background(), userID)
		h.ClearLastSeenDebounce(context.Background(), userID)

		defer func() {
			ctx := context.Background()
			h.ClearPresence(ctx, userID)
			if h.redisClient != nil {
				_ = h.redisClient.Publish(ctx, ChannelUserOffline, userID).Err()
			}
			h.ScheduleLastSeenDebounce(ctx, userID, token)
			h.Unregister(userID, c)
			close(c.Send)
		}()
		go c.RunWritePump()
		// Read client messages: typing_start/typing_stop -> publish to Redis; other types ignored for now.
		for {
			_, raw, err := conn.ReadMessage()
			if err != nil {
				return
			}
			var in clientIncoming
			if err := json.Unmarshal(raw, &in); err != nil {
				continue // ignore malformed
			}
			if in.Type == "ping" {
				h.RefreshPresence(context.Background(), userID)
				select {
				case c.Send <- []byte(`{"type":"pong"}`):
				default:
				}
				continue
			}
			if in.Type == "typing_start" && in.ConversationID != "" && in.RecipientID != "" {
				payload := TypingPayload{
					Type:            "typing_start",
					UserID:          userID,
					ConversationID:  in.ConversationID,
					RecipientID:     in.RecipientID,
					FullName:        in.FullName,
				}
				body, _ := json.Marshal(payload)
				h.PublishTyping(context.Background(), in.ConversationID, body)
			}
			if in.Type == "typing_stop" && in.ConversationID != "" && in.RecipientID != "" {
				payload := TypingPayload{
					Type:            "typing_stop",
					UserID:          userID,
					ConversationID:  in.ConversationID,
					RecipientID:     in.RecipientID,
					FullName:        in.FullName,
				}
				body, _ := json.Marshal(payload)
				h.PublishTyping(context.Background(), in.ConversationID, body)
			}
		}
	}
}

// PublishChatMessage is called when we receive from Redis; payload is JSON string.
func (h *Hub) PublishChatMessage(payload []byte) {
	var msg ChatMessage
	if err := json.Unmarshal(payload, &msg); err != nil {
		log.Printf("redis chat payload unmarshal: %v", err)
		return
	}
	// Send to recipient (1:1). Optionally also echo to sender if needed.
	h.SendToUser(msg.RecipientID, payload)
}
