// chat-ws: WebSocket server for real-time chat.
// Connects with ?token=JWT (same SECRET_KEY as Python). Subscribes to Redis chat:conversation:* and forwards to connected clients.
package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"

	redisv9 "github.com/redis/go-redis/v9"

	"linkup/chat-ws/internal/api"
	"linkup/chat-ws/internal/config"
	"linkup/chat-ws/internal/hub"
	"linkup/chat-ws/internal/redis"
)

func main() {
	cfg := config.LoadConfig()
	if cfg.SecretKey == "" {
		log.Fatal("SECRET_KEY (or JWT_SECRET) is required")
	}

	opt, err := redisv9.ParseURL(cfg.RedisURL)
	if err != nil {
		log.Fatalf("redis parse URL: %v", err)
	}
	redisClient := redisv9.NewClient(opt)
	defer redisClient.Close()
	redisOfflineSub := redisv9.NewClient(opt)
	defer redisOfflineSub.Close()

	h := hub.NewHub(redisClient)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go redis.RunSubscriber(ctx, redisClient, h)
	go h.RunUserOfflineSubscriber(ctx, redisOfflineSub)
	go h.RunLastSeenDebounceWorker(ctx, cfg)

	http.HandleFunc("/ws", h.HandleWS(cfg))
	http.HandleFunc("/presence/", api.HandlePresence(cfg, redisClient))
	addr := ":" + strconv.Itoa(cfg.Port)
	log.Printf("chat-ws listening on %s (WS /ws, HTTP GET /presence/{userID})", addr)

	go func() {
		if err := http.ListenAndServe(addr, nil); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("shutting down...")
	cancel()
}
