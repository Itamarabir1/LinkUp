package hub

import (
	"log/slog"
	"sync"
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
	maxMessageSize = 8192
)

// Conn represents a WebSocket connection for a user.
type Conn struct {
	UserID    string
	Conn      *websocket.Conn
	Send      chan []byte
	done      chan struct{}
	closeOnce sync.Once
}

// Close signals the write pump to stop. Safe to call from any goroutine, any number of times.
func (c *Conn) Close() {
	c.closeOnce.Do(func() { close(c.done) })
}

// Done returns a receive-only channel that is closed when Close() is called.
func (c *Conn) Done() <-chan struct{} {
	return c.done
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
		case <-c.Done():
			c.Conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
			return
		case message := <-c.Send:
			c.Conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.Conn.WriteMessage(websocket.TextMessage, message); err != nil {
				return
			}

			// Drain queued messages — each as a separate frame
			n := len(c.Send)
			for i := 0; i < n; i++ {
				if err := c.Conn.WriteMessage(websocket.TextMessage, <-c.Send); err != nil {
					return
				}
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
