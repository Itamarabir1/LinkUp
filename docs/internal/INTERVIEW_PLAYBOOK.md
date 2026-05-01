# LinkUp — Interview Playbook (ניווט לראיונות)

מסמך זה הוא **נקודת כניסה אחת** לפני ראיון: מה לקרוא, לפי נושא, ואיך לספר את הסיפור ("מה בניתי" + "למה כך" + "מה הייתי עושה אחרת").

## שלושת השכבות (מומלץ להבין את הסדר)

| שכבה | מטרה | מסמך |
|------|--------|------|
| **1 — Pitch + פיצ'רים** | "מה יש במוצר ומה הדגשים הטכניים" | [ENGINEERING_HIGHLIGHTS.md](../ENGINEERING_HIGHLIGHTS.md) |
| **2 — למה ואלטרנטיבות (לפי פיצ'ר)** | טבלת Why / Alternatives / Trade-offs ממוקדת | [FEATURE_DECISIONS.md](../FEATURE_DECISIONS.md) |
| **3 — החלטות ADR (עומק)** | פורמט ADR: הקשר, החלטה, סקייל, אלטרנטיבה | [adr/ARCHITECTURE_DECISIONS_BACKEND.md](../adr/ARCHITECTURE_DECISIONS_BACKEND.md), [adr/ARCHITECTURE_DECISIONS_FRONTEND.md](../adr/ARCHITECTURE_DECISIONS_FRONTEND.md), [adr/ARCHITECTURE_DECISIONS_CHAT_WS.md](../adr/ARCHITECTURE_DECISIONS_CHAT_WS.md) |

מפת CV ↔ מסמכים: [INTERVIEW_TECH_STACK_MAP.md](INTERVIEW_TECH_STACK_MAP.md).

---

## מסלולי קריאה לפי סוג ראיון

### System design / Backend / Staff

1. [../ARCHITECTURE.md](../ARCHITECTURE.md) — שירותים, Redis DB0/DB1, Outbox, תבניות.
2. [FEATURE_DECISIONS.md](../FEATURE_DECISIONS.md) — Outbox, Idempotency (`request-ride-from-search`, [chat message POST](../FEATURE_DECISIONS.md#chat-message-idempotency)), JWT denylist, Circuit Breaker, Sentry, Prometheus/Grafana, **PgBouncer**, **Redis Sentinel HA**, **Single-EC2 CD rolling deploy** + chat plaintext + chat rate limit + [chat inbox N+1 fix](../FEATURE_DECISIONS.md#chat-inbox-n1) + [chat WS `onOpen` REST backfill](../FEATURE_DECISIONS.md#chat-thread-reconnect).
3. [adr/ARCHITECTURE_DECISIONS_BACKEND.md](../adr/ARCHITECTURE_DECISIONS_BACKEND.md) — §1–§25 (כולל idempotency צ’אט §25, audit §24, וכו’).
4. אם שואלים על message reliability depth: [FEATURE_DECISIONS.md — RabbitMQ reliability refactor](../FEATURE_DECISIONS.md#rabbitmq-pr1-pr2) + [architecture/EVENTS.md](../architecture/EVENTS.md) (Connection Topology / Retry / DLQ).

### Real-time / WebSocket

1. [architecture/REALTIME.md](../architecture/REALTIME.md)
2. [adr/WEBSOCKETS.md](../adr/WEBSOCKETS.md), [adr/ARCHITECTURE_DECISIONS_CHAT_WS.md](../adr/ARCHITECTURE_DECISIONS_CHAT_WS.md) (כולל **§7** — גודל מסר נכנס + דילול typing)
3. [FEATURE_DECISIONS.md — צ'אט ו-chat-ws](../FEATURE_DECISIONS.md#chat-ws), [FEATURE_DECISIONS.md — Chat rate limit](../FEATURE_DECISIONS.md#chat-rate-limit), [chat thread reconnect backfill](../FEATURE_DECISIONS.md#chat-thread-reconnect)
4. [FEATURE_DECISIONS.md — Redis Sentinel HA](../FEATURE_DECISIONS.md#redis-sentinel)

### Frontend / Product engineer

1. [../../frontend/docs/ARCHITECTURE.md](../../frontend/docs/ARCHITECTURE.md)
2. [adr/ARCHITECTURE_DECISIONS_FRONTEND.md](../adr/ARCHITECTURE_DECISIONS_FRONTEND.md)
3. [../../frontend/docs/FRONTEND_REFACTOR_AND_QUALITY.md](../../frontend/docs/FRONTEND_REFACTOR_AND_QUALITY.md)

### Security

1. [ERRORS.md](../ERRORS.md) — פורמט `LinkupError`, `trace_id`
2. [FEATURE_DECISIONS.md — Auth](../FEATURE_DECISIONS.md#auth-session)
3. ADR Backend §12 (auth עומס), §18 (denylist), §22 (chat plaintext)

### DevOps / Reliability

1. [ENGINEERING_HIGHLIGHTS.md](../ENGINEERING_HIGHLIGHTS.md) — סעיפי CI/CD, health, DLQ
2. [architecture/EVENTS.md](../architecture/EVENTS.md) — retry, DLQ, scheduled
3. Root [../README.md](../README.md) — GitHub Actions / GHCR
4. [FEATURE_DECISIONS.md#pgbouncer](../FEATURE_DECISIONS.md#pgbouncer) + [FEATURE_DECISIONS.md#redis-sentinel](../FEATURE_DECISIONS.md#redis-sentinel) + [FEATURE_DECISIONS.md#single-ec2-cd](../FEATURE_DECISIONS.md#single-ec2-cd) — rollout considerations ב-EC2 (pooling + Redis HA + automated CD/rollback)

---

## איך להשתמש בזה ב-5 דקות לפני ראיון

1. פתח [FEATURE_DECISIONS.md](../FEATURE_DECISIONS.md) ובחר 3 נושאים שמופיעים ב-CV / בפרויקט שתדגים.
2. לכל נושא: קרא עמודה **Interview pitch (≈30s)** + אם שואלים עומק — ADR או § ב-HIGHLIGHTS.
3. שמור משפט אחד על **trade-off** (מה ויתרת ולמה).

---

## קישורים מסכמים

- מדריך ADR (סדר קריאה): [adr/README.md](../adr/README.md)
- שגיאות: [ERRORS.md](../ERRORS.md)
- API: [architecture/API.md](../architecture/API.md)
- DB: [architecture/DATABASE.md](../architecture/DATABASE.md)


