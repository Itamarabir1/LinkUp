package hub

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"

	"linkup/chat-ws/internal/config"
)

// ChannelUserOffline — publish payload = user_id (string); כל מופעי chat-ws מקבלים ומשדרים WS ללקוחות.
const ChannelUserOffline = "user:offline"

// ChannelUserOnline — payload = user_id (string); broadcast WS user_online לכל המחוברים.
const ChannelUserOnline = "user:online"

// Hub maps user_id (UUID string) -> list of connections (one user can have multiple devices).
type Hub struct {
	mu          sync.RWMutex
	users       map[string][]*Conn
	redisClient *redis.Client
}

// NewHub creates a Hub. redisClient is used to publish typing events; can be nil (typing disabled).
func NewHub(redisClient *redis.Client) *Hub {
	return &Hub{
		users:       make(map[string][]*Conn),
		redisClient: redisClient,
	}
}

// Register adds a connection for userID.
func (h *Hub) Register(userID string, c *Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.users[userID] = append(h.users[userID], c)
}

// Unregister removes a connection.
func (h *Hub) Unregister(userID string, c *Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()
	list := h.users[userID]
	for i, x := range list {
		if x == c {
			h.users[userID] = append(list[:i], list[i+1:]...)
			if len(h.users[userID]) == 0 {
				delete(h.users, userID)
			}
			break
		}
	}
}

// PublishTyping publishes a typing event to Redis channel chat:typing:{conversationID}. No-op if redisClient is nil.
func (h *Hub) PublishTyping(ctx context.Context, conversationID string, payload []byte) {
	if h.redisClient == nil {
		return
	}
	channel := "chat:typing:" + conversationID
	if err := h.redisClient.Publish(ctx, channel, payload).Err(); err != nil {
		slog.Error("redis publish typing failed", "component", "hub", "op", "PublishTyping", "error_code", "REDIS_PUBLISH_FAILED", "err", err)
	}
}

// SetPresence marks user as online in Redis with TTL.
func (h *Hub) SetPresence(ctx context.Context, userID string) {
	if h.redisClient == nil {
		return
	}
	if err := h.redisClient.Set(ctx, "presence:"+userID, "1", 60*time.Second).Err(); err != nil {
		slog.Error("redis SetPresence failed", "component", "hub", "op", "SetPresence", "error_code", "REDIS_SET_FAILED", "err", err)
	}
}

// RefreshPresence extends TTL for user's presence key.
func (h *Hub) RefreshPresence(ctx context.Context, userID string) {
	if h.redisClient == nil {
		return
	}
	if err := h.redisClient.Expire(ctx, "presence:"+userID, 60*time.Second).Err(); err != nil {
		slog.Error("redis RefreshPresence failed", "component", "hub", "op", "RefreshPresence", "error_code", "REDIS_EXPIRE_FAILED", "err", err)
	}
}

// ClearPresence removes user's presence key.
func (h *Hub) ClearPresence(ctx context.Context, userID string) {
	if h.redisClient == nil {
		return
	}
	if err := h.redisClient.Del(ctx, "presence:"+userID).Err(); err != nil {
		slog.Error("redis ClearPresence failed", "component", "hub", "op", "ClearPresence", "error_code", "REDIS_DEL_FAILED", "err", err)
	}
}

const (
	debounceLastSeenKeyPrefix = "debounce:last_seen:"
	lastSeenHoldKeyPrefix     = "last_seen:hold:"
	lastSeenTokenKeyPrefix    = "last_seen:token:"
)

// ClearLastSeenDebounce removes debounce keys on (re)connect so a quick reconnect cancels pending PATCH.
func (h *Hub) ClearLastSeenDebounce(ctx context.Context, userID string) {
	if h.redisClient == nil {
		return
	}
	if err := h.redisClient.Del(
		ctx,
		debounceLastSeenKeyPrefix+userID,
		lastSeenHoldKeyPrefix+userID,
		lastSeenTokenKeyPrefix+userID,
	).Err(); err != nil {
		slog.Error("redis ClearLastSeenDebounce failed", "component", "hub", "op", "ClearLastSeenDebounce", "error_code", "REDIS_DEL_FAILED", "err", err)
	}
}

// ScheduleLastSeenDebounce stores token in Redis: debounce key EX 10s; hold key keeps token until worker PATCH.
func (h *Hub) ScheduleLastSeenDebounce(ctx context.Context, userID, token string) {
	if h.redisClient == nil || token == "" {
		return
	}
	if err := h.redisClient.Set(ctx, debounceLastSeenKeyPrefix+userID, token, 10*time.Second).Err(); err != nil {
		slog.Error("redis ScheduleLastSeenDebounce debounce failed", "component", "hub", "op", "ScheduleLastSeenDebounce", "error_code", "REDIS_SET_FAILED", "err", err)
	}
	if err := h.redisClient.Set(ctx, lastSeenHoldKeyPrefix+userID, token, 25*time.Second).Err(); err != nil {
		slog.Error("redis ScheduleLastSeenDebounce hold failed", "component", "hub", "op", "ScheduleLastSeenDebounce", "error_code", "REDIS_SET_FAILED", "err", err)
	}
	if err := h.redisClient.Set(ctx, lastSeenTokenKeyPrefix+userID, token, 25*time.Second).Err(); err != nil {
		slog.Error("redis ScheduleLastSeenDebounce token failed", "component", "hub", "op", "ScheduleLastSeenDebounce", "error_code", "REDIS_SET_FAILED", "err", err)
	}
}

// RunLastSeenDebounceWorker every 5s: for each last_seen:hold:*, if debounce key is gone, PATCH backend and DEL hold.
func (h *Hub) RunLastSeenDebounceWorker(ctx context.Context, cfg config.Config) {
	if h.redisClient == nil || cfg.BackendURL == "" {
		return
	}
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			h.flushDueLastSeen(ctx, cfg)
		}
	}
}

func (h *Hub) flushDueLastSeen(ctx context.Context, cfg config.Config) {
	if h.redisClient == nil {
		return
	}
	var cursor uint64
	for {
		keys, next, err := h.redisClient.Scan(ctx, cursor, lastSeenHoldKeyPrefix+"*", 64).Result()
		if err != nil {
			slog.Error("redis flushDueLastSeen Scan failed", "component", "hub", "op", "flushDueLastSeen", "error_code", "REDIS_SCAN_FAILED", "err", err)
			return
		}
		for _, key := range keys {
			userID := strings.TrimPrefix(key, lastSeenHoldKeyPrefix)
			if userID == "" {
				continue
			}
			n, err := h.redisClient.Exists(ctx, debounceLastSeenKeyPrefix+userID).Result()
			if err != nil || n > 0 {
				continue
			}
			tokenKey := lastSeenTokenKeyPrefix + userID
			token, err := h.redisClient.Get(ctx, tokenKey).Result()
			if err != nil || token == "" {
				token, err = h.redisClient.Get(ctx, key).Result()
			}
			if err != nil || token == "" {
				if _, delErr := h.redisClient.Del(ctx, key, tokenKey).Result(); delErr != nil {
					slog.Error("redis flushDueLastSeen Del stale failed", "component", "hub", "op", "flushDueLastSeen", "error_code", "REDIS_DEL_FAILED", "err", delErr)
				}
				continue
			}
			reqCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
			endpoint := cfg.BackendURL + "/api/v1/users/me/last-seen"
			req, err := http.NewRequestWithContext(reqCtx, http.MethodPatch, endpoint, nil)
			if err != nil {
				cancel()
				slog.Error("flushDueLastSeen NewRequest failed", "component", "hub", "op", "flushDueLastSeen", "error_code", "HTTP_REQUEST_BUILD_FAILED", "err", err)
				continue
			}
			req.Header.Set("Authorization", "Bearer "+token)
			client := &http.Client{Timeout: 2 * time.Second}
			resp, err := client.Do(req)
			if err != nil {
				slog.Error("flushDueLastSeen PATCH last-seen failed", "component", "hub", "op", "flushDueLastSeen", "error_code", "BACKEND_PATCH_FAILED", "err", err)
			}
			ok := err == nil && resp != nil && resp.StatusCode >= 200 && resp.StatusCode < 300
			if resp != nil && resp.Body != nil {
				if closeErr := resp.Body.Close(); closeErr != nil {
					slog.Error("flushDueLastSeen body close failed", "component", "hub", "op", "flushDueLastSeen", "error_code", "HTTP_BODY_CLOSE_FAILED", "err", closeErr)
				}
			}
			cancel()
			if ok {
				if _, delErr := h.redisClient.Del(ctx, key, tokenKey).Result(); delErr != nil {
					slog.Error("redis flushDueLastSeen Del after ok failed", "component", "hub", "op", "flushDueLastSeen", "error_code", "REDIS_DEL_FAILED", "err", delErr)
				}
			}
		}
		cursor = next
		if cursor == 0 {
			break
		}
	}
}

// PublishTypingMessage is called when we receive a typing event from Redis; payload is JSON. Sends to recipient.
func (h *Hub) PublishTypingMessage(payload []byte) {
	var msg TypingPayload
	if err := json.Unmarshal(payload, &msg); err != nil {
		slog.Error("redis typing payload unmarshal failed", "component", "hub", "op", "PublishTypingMessage", "error_code", "REDIS_TYPING_PAYLOAD_INVALID", "err", err)
		return
	}
	h.SendToUser(msg.RecipientID, payload)
}

// RunUserOfflineSubscriber — לקוח Redis נפרד מ-PSubscribe של הצ'אט (מומלץ go-redis).
func (h *Hub) RunUserOfflineSubscriber(ctx context.Context, subClient *redis.Client) {
	if subClient == nil {
		return
	}
	pubsub := subClient.Subscribe(ctx, ChannelUserOffline)
	defer pubsub.Close()
	ch := pubsub.Channel()
	for {
		select {
		case <-ctx.Done():
			return
		case msg, ok := <-ch:
			if !ok {
				return
			}
			if msg == nil {
				continue
			}
			uid := strings.TrimSpace(msg.Payload)
			if uid == "" {
				continue
			}
			h.broadcastOffline(uid)
		}
	}
}

func (h *Hub) RunUserOnlineSubscriber(ctx context.Context, subClient *redis.Client) {
	if subClient == nil {
		return
	}
	pubsub := subClient.Subscribe(ctx, ChannelUserOnline)
	defer pubsub.Close()
	ch := pubsub.Channel()
	for {
		select {
		case <-ctx.Done():
			return
		case msg, ok := <-ch:
			if !ok {
				return
			}
			if msg == nil {
				continue
			}
			uid := strings.TrimSpace(msg.Payload)
			if uid == "" {
				continue
			}
			h.broadcastOnline(uid)
		}
	}
}

func (h *Hub) broadcastOnline(onlineUserID string) {
	payload, err := json.Marshal(map[string]string{
		"type":    "user_online",
		"user_id": onlineUserID,
	})
	if err != nil {
		slog.Error("broadcastOnline marshal failed", "component", "hub", "op", "broadcastOnline", "error_code", "JSON_MARSHAL_FAILED", "err", err)
		return
	}
	h.mu.RLock()
	var conns []*Conn
	for _, list := range h.users {
		for _, c := range list {
			conns = append(conns, c)
		}
	}
	h.mu.RUnlock()
	for _, c := range conns {
		select {
		case c.Send <- payload:
		default:
		}
	}
}

func (h *Hub) broadcastOffline(offlineUserID string) {
	payload, err := json.Marshal(map[string]string{
		"type":    "user_offline",
		"user_id": offlineUserID,
	})
	if err != nil {
		slog.Error("broadcastOffline marshal failed", "component", "hub", "op", "broadcastOffline", "error_code", "JSON_MARSHAL_FAILED", "err", err)
		return
	}
	h.mu.RLock()
	var conns []*Conn
	for _, list := range h.users {
		for _, c := range list {
			conns = append(conns, c)
		}
	}
	h.mu.RUnlock()
	for _, c := range conns {
		select {
		case c.Send <- payload:
		default:
		}
	}
}

// SendToUser sends a JSON message to all connections of the given user.
func (h *Hub) SendToUser(userID string, payload []byte) {
	h.mu.RLock()
	conns := h.users[userID]
	// copy so we don't hold lock while writing
	if len(conns) > 0 {
		conns = append([]*Conn(nil), conns...)
	}
	h.mu.RUnlock()
	for _, c := range conns {
		select {
		case c.Send <- payload:
		default:
			// buffer full, skip (or close conn)
		}
	}
}
