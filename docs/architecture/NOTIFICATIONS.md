# Notifications Architecture (Placeholder)

This file will be the canonical notification design doc.

## Scope (to be expanded)

- Outbox -> RabbitMQ routing for notification events
- Email channel (Brevo + email-renderer)
- Push channel (FCM)
- In-app notification websocket feed (`/api/v1/notifications/ws`)
- Retry / DLQ / replay strategy
- Delivery observability and alerting

## Current references

- [`docs/architecture/EVENTS.md`](EVENTS.md)
- [`docs/FCM_SYSTEM_SUMMARY.md`](../FCM_SYSTEM_SUMMARY.md)
- [`docs/DEPLOYMENT.md`](../DEPLOYMENT.md)
