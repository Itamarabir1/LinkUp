package redis

import (
	"context"
	"log/slog"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"

	"linkup/chat-ws/internal/hub"
	"linkup/chat-ws/internal/safego"
)

const (
	ChatChannelPattern   = "chat:conversation:*"
	TypingChannelPattern = "chat:typing:*"
	UserEventPattern     = "user:*:events"
)

func RunSubscriber(ctx context.Context, client *redis.Client, h *hub.Hub) {
	defer safego.RecoverPanic("redis", "RunSubscriber")
	backoff := time.Second
	const maxBackoff = 30 * time.Second
	for {
		if ctx.Err() != nil {
			return
		}
		start := time.Now()
		runOnce(ctx, client, h)
		if ctx.Err() != nil {
			return
		}
		if time.Since(start) > maxBackoff {
			backoff = time.Second
		}
		slog.Warn("redis subscriber disconnected, reconnecting", "backoff", backoff)
		select {
		case <-ctx.Done():
			return
		case <-time.After(backoff):
		}
		backoff *= 2
		if backoff > maxBackoff {
			backoff = maxBackoff
		}
	}
}

func runOnce(ctx context.Context, client *redis.Client, h *hub.Hub) {
	pubsub := client.PSubscribe(ctx, ChatChannelPattern, TypingChannelPattern, UserEventPattern)
	defer pubsub.Close()
	ch := pubsub.Channel()
	h.MarkSubAlive(hub.SubChat)
	for {
		select {
		case <-ctx.Done():
			return
		case msg, ok := <-ch:
			if !ok {
				return
			}
			payload := []byte(msg.Payload)
			switch {
			case strings.HasPrefix(msg.Channel, "chat:typing:"):
				h.PublishTypingMessage(payload)
			case strings.HasPrefix(msg.Channel, "user:") && strings.HasSuffix(msg.Channel, ":events"):
				userID := strings.TrimPrefix(msg.Channel, "user:")
				userID = strings.TrimSuffix(userID, ":events")
				h.SendToUser(userID, payload)
			default:
				h.PublishChatMessage(payload)
			}
		}
	}
}
