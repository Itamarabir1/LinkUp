package hub

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"time"

	"github.com/gorilla/websocket"
	"golang.org/x/time/rate"

	"linkup/chat-ws/internal/api"
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

func wsUpgrader(cfg config.Config) websocket.Upgrader {
	return websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			origin := r.Header.Get("Origin")
			if len(cfg.AllowedOrigins) == 0 {
				return true
			}
			if origin == "" {
				return true
			}
			for _, o := range cfg.AllowedOrigins {
				if o == origin {
					return true
				}
			}
			return false
		},
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
	}
}

func closeWS(conn *websocket.Conn, code int, reason string) {
	deadline := time.Now().Add(2 * time.Second)
	msg := websocket.FormatCloseMessage(code, reason)
	_ = conn.WriteControl(websocket.CloseMessage, msg, deadline)
}

// HandleWS upgrades HTTP to WebSocket. Query: token=JWT. Validates token and registers connection.
func (h *Hub) HandleWS(cfg config.Config) http.HandlerFunc {
	upgrader := wsUpgrader(cfg)
	return func(w http.ResponseWriter, r *http.Request) {
		token := r.URL.Query().Get("token")
		if token == "" {
			api.WriteAPIError(w, r, http.StatusUnauthorized, "UNAUTHORIZED", "חסר אסימון")
			return
		}
		userID, err := auth.ValidateToken(token, cfg.SecretKey, cfg.JWTAlg)
		if err != nil {
			api.WriteAPIError(w, r, http.StatusUnauthorized, "INVALID_TOKEN", "אסימון לא תקף")
			return
		}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			slog.Error("ws upgrade failed", "component", "hub", "op", "Upgrade", "error_code", "WS_UPGRADE_FAILED", "err", err)
			return
		}
		conn.SetReadLimit(int64(maxMessageSize))
		typingLimiter := rate.NewLimiter(rate.Limit(30), 60)
		c := &Conn{UserID: userID, Conn: conn, Send: make(chan []byte, 256), done: make(chan struct{})}
		h.Register(userID, c)
		h.SetPresence(context.Background(), userID)
		h.ClearLastSeenDebounce(context.Background(), userID)
		if h.redisClient != nil {
			if pubErr := h.redisClient.Publish(context.Background(), ChannelUserOnline, userID).Err(); pubErr != nil {
				slog.Error("redis publish user online failed", "component", "hub", "op", "PublishUserOnline", "error_code", "REDIS_PUBLISH_FAILED", "err", pubErr)
			}
		}

		defer func() {
			ctx := context.Background()
			h.ClearPresence(ctx, userID)
			if h.redisClient != nil {
				if pubErr := h.redisClient.Publish(ctx, ChannelUserOffline, userID).Err(); pubErr != nil {
					slog.Error("redis publish user offline failed", "component", "hub", "op", "PublishUserOffline", "error_code", "REDIS_PUBLISH_FAILED", "err", pubErr)
				}
			}
			h.ScheduleLastSeenDebounce(ctx, userID, token)
			h.Unregister(userID, c)
			close(c.done)
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
				slog.Error("ws client json invalid", "component", "hub", "op", "ReadLoop", "error_code", "WS_INVALID_PAYLOAD", "err", err)
				closeWS(conn, websocket.ClosePolicyViolation, "invalid json")
				return
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
				if !typingLimiter.Allow() {
					continue
				}
				payload := TypingPayload{
					Type:           "typing_start",
					UserID:         userID,
					ConversationID: in.ConversationID,
					RecipientID:    in.RecipientID,
					FullName:       in.FullName,
				}
				body, mErr := json.Marshal(payload)
				if mErr != nil {
					slog.Error("ws typing_start marshal failed", "component", "hub", "op", "MarshalTyping", "error_code", "WS_INTERNAL_ERROR", "err", mErr)
					closeWS(conn, websocket.CloseInternalServerErr, "marshal failed")
					return
				}
				h.PublishTyping(context.Background(), in.ConversationID, body)
			}
			if in.Type == "typing_stop" && in.ConversationID != "" && in.RecipientID != "" {
				if !typingLimiter.Allow() {
					continue
				}
				payload := TypingPayload{
					Type:           "typing_stop",
					UserID:         userID,
					ConversationID: in.ConversationID,
					RecipientID:    in.RecipientID,
					FullName:       in.FullName,
				}
				body, mErr := json.Marshal(payload)
				if mErr != nil {
					slog.Error("ws typing_stop marshal failed", "component", "hub", "op", "MarshalTyping", "error_code", "WS_INTERNAL_ERROR", "err", mErr)
					closeWS(conn, websocket.CloseInternalServerErr, "marshal failed")
					return
				}
				h.PublishTyping(context.Background(), in.ConversationID, body)
			}
		}
	}
}

// PublishChatMessage is called when we receive from Redis; payload is JSON string.
func (h *Hub) PublishChatMessage(payload []byte) {
	var msg ChatMessage
	if err := json.Unmarshal(payload, &msg); err != nil {
		slog.Error("redis chat payload unmarshal failed", "component", "hub", "op", "PublishChatMessage", "error_code", "REDIS_CHAT_PAYLOAD_INVALID", "err", err)
		return
	}
	// Send to recipient (1:1). Optionally also echo to sender if needed.
	h.SendToUser(msg.RecipientID, payload)
}
