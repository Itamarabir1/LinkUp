# Build stage
FROM golang:1.23-alpine AS builder
WORKDIR /app

# Copy go.mod first (needed for module resolution)
COPY go.mod go.sum ./
RUN go mod download

# Copy source code directories (preserving module structure)
COPY cmd/ ./cmd/
COPY internal/ ./internal/

# Build the application
# Module name is "linkup/chat-ws", main.go is in cmd/server/
# The build command looks for main.go in ./cmd/server/ directory
RUN CGO_ENABLED=0 GOOS=linux go build -o /chat-ws ./cmd/server

# Run stage
FROM alpine:3.19
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /chat-ws .
RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
    && chown appuser:appgroup /app/chat-ws
USER appuser
EXPOSE 8081
CMD ["./chat-ws"]
