package hub

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"

	"linkup/chat-ws/internal/config"
)

// ChannelUserOffline — publish payload = user_id (string); כל מופעי chat-ws מקבלים ומשדרים WS ללקוחות.
const ChannelUserOffline = "user:offline"

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
		return // log optional
	}
}

// SetPresence marks user as online in Redis with TTL.
func (h *Hub) SetPresence(ctx context.Context, userID string) {
	if h.redisClient == nil {
		return
	}
	_ = h.redisClient.Set(ctx, "presence:"+userID, "1", 60*time.Second).Err()
}

// RefreshPresence extends TTL for user's presence key.
func (h *Hub) RefreshPresence(ctx context.Context, userID string) {
	if h.redisClient == nil {
		return
	}
	_ = h.redisClient.Expire(ctx, "presence:"+userID, 60*time.Second).Err()
}

// ClearPresence removes user's presence key.
func (h *Hub) ClearPresence(ctx context.Context, userID string) {
	if h.redisClient == nil {
		return
	}
	_ = h.redisClient.Del(ctx, "presence:"+userID).Err()
}

const (
	debounceLastSeenKeyPrefix = "debounce:last_seen:"
	lastSeenHoldKeyPrefix     = "last_seen:hold:"
)

// ClearLastSeenDebounce removes debounce keys on (re)connect so a quick reconnect cancels pending PATCH.
func (h *Hub) ClearLastSeenDebounce(ctx context.Context, userID string) {
	if h.redisClient == nil {
		return
	}
	_ = h.redisClient.Del(ctx, debounceLastSeenKeyPrefix+userID, lastSeenHoldKeyPrefix+userID).Err()
}

// ScheduleLastSeenDebounce stores token in Redis: debounce key EX 10s; hold key keeps token until worker PATCH.
func (h *Hub) ScheduleLastSeenDebounce(ctx context.Context, userID, token string) {
	if h.redisClient == nil || token == "" {
		return
	}
	_ = h.redisClient.Set(ctx, debounceLastSeenKeyPrefix+userID, token, 10*time.Second).Err()
	_ = h.redisClient.Set(ctx, lastSeenHoldKeyPrefix+userID, token, 25*time.Second).Err()
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
			token, err := h.redisClient.Get(ctx, key).Result()
			if err != nil || token == "" {
				_, _ = h.redisClient.Del(ctx, key).Result()
				continue
			}
			reqCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
			endpoint := cfg.BackendURL + "/api/v1/users/me/last-seen"
			req, err := http.NewRequestWithContext(reqCtx, http.MethodPatch, endpoint, nil)
			if err != nil {
				cancel()
				continue
			}
			req.Header.Set("Authorization", "Bearer "+token)
			client := &http.Client{Timeout: 2 * time.Second}
			resp, err := client.Do(req)
			if resp != nil && resp.Body != nil {
				_ = resp.Body.Close()
			}
			cancel()
			_, _ = h.redisClient.Del(ctx, key).Result()
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
		log.Printf("redis typing payload unmarshal: %v", err)
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

func (h *Hub) broadcastOffline(offlineUserID string) {
	payload, err := json.Marshal(map[string]string{
		"type":    "user_offline",
		"user_id": offlineUserID,
	})
	if err != nil {
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
