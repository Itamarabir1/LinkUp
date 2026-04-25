"""
LinkUp Prometheus metrics — single source of truth.
Import from here in all domain/infra modules.
"""

from prometheus_client import Counter, Gauge, Histogram

# =============================================================================
# RabbitMQ
# =============================================================================
rabbitmq_messages_consumed_total = Counter(
    "rabbitmq_messages_consumed_total",
    "Messages processed successfully",
    ["queue"],
)
rabbitmq_messages_failed_total = Counter(
    "rabbitmq_messages_failed_total",
    "Messages that failed processing",
    ["queue"],
)
rabbitmq_messages_retried_total = Counter(
    "rabbitmq_messages_retried_total",
    "Messages sent to retry queue",
    ["queue"],
)
rabbitmq_dlq_depth = Gauge(
    "rabbitmq_dlq_depth",
    "Number of messages waiting in DLQ",
    ["queue"],
)
rabbitmq_consumer_restarts_total = Counter(
    "rabbitmq_consumer_restarts_total",
    "Number of times supervisor restarted a consumer",
    ["worker"],
)
rabbitmq_consumer_iterator_restarts_total = Counter(
    "rabbitmq_consumer_iterator_restarts_total",
    "Number of times consumer recreated its queue iterator after channel/iterator close",
    ["queue"],
)

# =============================================================================
# Outbox
# =============================================================================
outbox_events_processed_total = Counter(
    "outbox_events_processed_total",
    "Outbox events processed successfully",
    ["event_name"],
)
outbox_events_failed_total = Counter(
    "outbox_events_failed_total",
    "Outbox events that failed",
    ["event_name"],
)
# DEFERRED: no call sites yet — intentional.
# Activation tracked in separate PR.
outbox_pending_depth = Gauge(
    "outbox_pending_depth",
    "Number of pending events in outbox",
)

# =============================================================================
# Notifications
# =============================================================================
notifications_sent_total = Counter(
    "notifications_sent_total",
    "Notifications sent successfully",
    ["channel"],
)
notifications_failed_total = Counter(
    "notifications_failed_total",
    "Notifications that failed to send",
    ["channel"],
)

# =============================================================================
# Billing
# =============================================================================
payments_initiated_total = Counter(
    "payments_initiated_total",
    "Stripe checkout sessions created",
)
payments_succeeded_total = Counter(
    "payments_succeeded_total",
    "Payments that succeeded",
)
payments_failed_total = Counter(
    "payments_failed_total",
    "Payments that failed",
)
stripe_webhook_received_total = Counter(
    "stripe_webhook_received_total",
    "Webhooks received from Stripe",
    ["event_type"],
)
stripe_webhook_errors_total = Counter(
    "stripe_webhook_errors_total",
    "Stripe webhooks that failed signature verification",
)

# =============================================================================
# Auth
# =============================================================================
auth_registrations_total = Counter(
    "auth_registrations_total",
    "New user registrations",
    ["provider"],
)
auth_logins_total = Counter(
    "auth_logins_total",
    "Successful logins",
    ["provider"],
)
auth_failures_total = Counter(
    "auth_failures_total",
    "Authentication failures",
    ["reason"],
)

# =============================================================================
# Rides
# =============================================================================
rides_created_total = Counter(
    "rides_created_total",
    "Rides created",
)
rides_cancelled_total = Counter(
    "rides_cancelled_total",
    "Rides cancelled",
    ["by"],
)
rides_completed_total = Counter(
    "rides_completed_total",
    "Rides completed",
)

# =============================================================================
# Bookings
# =============================================================================
bookings_created_total = Counter(
    "bookings_created_total",
    "Booking requests created",
)
bookings_approved_total = Counter(
    "bookings_approved_total",
    "Bookings approved by driver",
)
bookings_rejected_total = Counter(
    "bookings_rejected_total",
    "Bookings rejected by driver",
)
bookings_cancelled_total = Counter(
    "bookings_cancelled_total",
    "Bookings cancelled",
)

# =============================================================================
# Geo
# =============================================================================
# DEFERRED: no call sites yet — intentional.
# Activation tracked in separate PR.
geo_requests_total = Counter(
    "geo_requests_total",
    "External geocoding API calls",
    ["type", "result"],
)
geo_cache_hits_total = Counter(
    "geo_cache_hits_total",
    "Geocoding cache hits",
)
geo_cache_misses_total = Counter(
    "geo_cache_misses_total",
    "Geocoding cache misses",
)
geo_circuit_breaker_state = Gauge(
    "geo_circuit_breaker_state",
    "Circuit breaker state: 0=closed, 1=half_open, 2=open",
    ["name"],
)

# =============================================================================
# S3
# =============================================================================
s3_uploads_total = Counter(
    "s3_uploads_total",
    "Files uploaded to S3",
    ["type"],
)
s3_uploads_failed_total = Counter(
    "s3_uploads_failed_total",
    "S3 uploads that failed",
    ["type"],
)

# =============================================================================
# AI
# =============================================================================
ai_chat_summaries_total = Counter(
    "ai_chat_summaries_total",
    "Chat summaries generated",
)
ai_chat_summaries_failed_total = Counter(
    "ai_chat_summaries_failed_total",
    "Chat summaries that failed",
)
ai_search_requests_total = Counter(
    "ai_search_requests_total",
    "AI ride search requests",
)
ai_search_failed_total = Counter(
    "ai_search_failed_total",
    "AI ride search requests that failed",
)

# Reserved for future latency instrumentation (not active yet)
noop_latency_histogram = Histogram(
    "noop_latency_histogram_seconds",
    "Reserved histogram for future latency metrics",
)
