// chat-ws: WebSocket server for real-time chat.
// Connects with ?token=JWT (same SECRET_KEY as Python). Subscribes to Redis chat:conversation:* and forwards to connected clients.
package main

import (
	"context"
	"log"
	"log/slog"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"strings"
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

	redisPassword, redisDB, err := parseRedisURL(cfg.RedisURL)
	if err != nil {
		log.Fatalf("redis URL parsing failed: %v", err)
	}
	redisClient := newRedisClient(cfg, redisPassword, redisDB)
	defer redisClient.Close()
	redisOfflineSub := newRedisClient(cfg, redisPassword, redisDB)
	defer redisOfflineSub.Close()
	redisOnlineSub := newRedisClient(cfg, redisPassword, redisDB)
	defer redisOnlineSub.Close()

	h := hub.NewHub(redisClient)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go redis.RunSubscriber(ctx, redisClient, h)
	go h.RunUserOfflineSubscriber(ctx, redisOfflineSub)
	go h.RunUserOnlineSubscriber(ctx, redisOnlineSub)
	go h.RunLastSeenDebounceWorker(ctx, cfg)

	http.HandleFunc("/ws", h.HandleWS(cfg))
	http.HandleFunc("/presence/", api.HandlePresence(cfg, redisClient))
	addr := ":" + strconv.Itoa(cfg.Port)
	slog.Info("chat-ws listening", "component", "server", "addr", addr, "ws", "/ws", "presence", "/presence/{userID}")

	go func() {
		if err := http.ListenAndServe(addr, nil); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	slog.Info("shutting down", "component", "server")
	cancel()
}

func newRedisClient(cfg config.Config, password string, db int) *redisv9.Client {
	return redisv9.NewClient(&redisv9.Options{
		Addr:     cfg.RedisAddr,
		Password: password,
		DB:       db,
	})
}

func parseRedisURL(raw string) (string, int, error) {
	parsed, err := url.Parse(raw)
	if err != nil {
		return "", 0, err
	}
	password := ""
	if parsed.User != nil {
		if pwd, ok := parsed.User.Password(); ok {
			password = pwd
		}
	}
	db := 0
	path := strings.TrimPrefix(parsed.Path, "/")
	if path != "" {
		v, convErr := strconv.Atoi(path)
		if convErr != nil {
			return "", 0, convErr
		}
		db = v
	}
	return password, db, nil
}
