package hub

import (
	"log/slog"
	"time"

	"github.com/gorilla/websocket"

	"linkup/chat-ws/internal/safego"
)

const (
	// Time allowed to write a message to the peer.
	writeWait = 10 * time.Second

	// Time allowed to read the next pong message from the peer.
	pongWait = 60 * time.Second

	// Send pings to peer with this period. Must be less than pongWait.
	pingPeriod = (pongWait * 9) / 10

	// Maximum message size allowed from peer.
	maxMessageSize = 2048
)

// Conn represents a WebSocket connection for a user.
type Conn struct {
	UserID string
	Conn   *websocket.Conn
	Send   chan []byte
	done   chan struct{}
}

// RunWritePump pumps messages from the hub to the websocket connection.
// A goroutine running RunWritePump is started for each connection.
func (c *Conn) RunWritePump() {
	defer safego.RecoverPanic("hub", "RunWritePump")
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		c.Conn.Close()
	}()

	for {
		select {
		case <-c.done:
			c.Conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
			return
		case message := <-c.Send:
			c.Conn.SetWriteDeadline(time.Now().Add(writeWait))
			w, err := c.Conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			w.Write(message)

			n := len(c.Send)
			for i := 0; i < n; i++ {
				w.Write([]byte{'\n'})
				w.Write(<-c.Send)
			}

			if err := w.Close(); err != nil {
				return
			}
		case <-ticker.C:
			c.Conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.Conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				slog.Error("websocket ping failed", "component", "hub", "op", "WritePump", "error_code", "WS_PING_FAILED", "user_id", c.UserID, "err", err)
				return
			}
		}
	}
}
