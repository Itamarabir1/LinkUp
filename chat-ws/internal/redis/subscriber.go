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
)

// RunSubscriber subscribes to chat:conversation:*, chat:typing:* and chat:notification:* and forwards messages to the Hub.
// Caller owns the client; RunSubscriber does not close it.
func RunSubscriber(ctx context.Context, client *redis.Client, h *hub.Hub) {
	pubsub := client.PSubscribe(ctx, ChatChannelPattern, TypingChannelPattern, NotifChannelPattern)
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
			} else {
				h.PublishChatMessage(payload)
			}
		}
	}
}
