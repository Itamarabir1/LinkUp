package redis

import (
	"context"
	"strings"

	"github.com/redis/go-redis/v9"

	"linkup/chat-ws/internal/hub"
)

const (
	ChatChannelPattern   = "chat:conversation:*"
	TypingChannelPattern = "chat:typing:*"
	NotifChannelPattern  = "chat:notification:*"
	UserEventPattern     = "user:*:events"
)

// RunSubscriber subscribes to chat/user event channels and forwards messages to the Hub.
// Caller owns the client; RunSubscriber does not close it.
func RunSubscriber(ctx context.Context, client *redis.Client, h *hub.Hub) {
	pubsub := client.PSubscribe(ctx, ChatChannelPattern, TypingChannelPattern, NotifChannelPattern, UserEventPattern)
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
			payload := []byte(msg.Payload)
			if strings.HasPrefix(msg.Channel, "chat:typing:") {
				h.PublishTypingMessage(payload)
			} else if strings.HasPrefix(msg.Channel, "chat:notification:") {
				recipientID := strings.TrimPrefix(msg.Channel, "chat:notification:")
				h.SendToUser(recipientID, payload)
			} else if strings.HasPrefix(msg.Channel, "user:") && strings.HasSuffix(msg.Channel, ":events") {
				userID := strings.TrimPrefix(msg.Channel, "user:")
				userID = strings.TrimSuffix(userID, ":events")
				h.SendToUser(userID, payload)
			} else {
				h.PublishChatMessage(payload)
			}
		}
	}
}
