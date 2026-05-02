# סיכום מלא — Billing Refactor

מקור ניסוח: סיכום מערכתי לשימור בתיעוד; מקור טכני בקוד תחת `backend/app/domain/billing/`.

---

## מה היה לפני

- Stripe Checkout + Postgres סינכרוני.
- אין state machine — סטטוס מתעדכן ישירות.
- אין reconciler — משתמש ששילם ולא קיבל premium נתקע לנצח.
- אין idempotency על checkout — לחיצה כפולה עלולה לגרום למצב לא עקבי (מספר sessions / תשלומים במסלולים מסויימים).
- `payments_failed_total` מוגדר אבל אף פעם לא נקרא.
- webhook מכסה רק `checkout.session.completed`.

---

## מה בנינו

### `state_machine.py`

`ALLOWED_TRANSITIONS` dict. כל מעבר סטטוס עובר `validate_transition`. מצבים טרמינליים (succeeded/failed/canceled) לא זזים לעולם. מגן מפני אירועים מאוחרים שמנסים לשנות סטטוס סגור.

### `stripe_gateway.py`

Stripe SDK מבודד לחלוטין. DTOs עם `slots=True`. שאר הקוד לא נוגע ב-SDK ישירות. מאפשר testing מלא בלי Stripe.

### `idempotency.py` + טבלת `idempotency_keys`

טבלה נפרדת — generic, reusable לכל endpoint עתידי. fingerprint + שמירת גוף תשובה + `status_code` + TTL. לחיצה כפולה (אותו מפתח + fingerprint) מחזירה cached response. mismatch על אותו key עם payload שונה מחזיר **422** (`IDEMPOTENCY_MISMATCH`).

### `reconciler.py`

רץ בתדירות קבועה דרך **APScheduler** ב־**`backend/app/core/lifespan.py`** (FastAPI lifespan; ברירת מחדל כל **10 דקות** — `BILLING_RECONCILER_INTERVAL_SECONDS=600`, ניתן לשינוי ב-env). **`BILLING_RECONCILER_ENABLED`** ברירת מחדל **`true`** ב־`app/core/config.py`; קבע ל־`false` כדי להשבית את התזמון.

- **PostgreSQL advisory lock** — cluster-safe; לא רצים פעמיים במקביל על מספר instances.
- **session נפרד לכל payment** — כשל על payment אחד לא משפיע על השאר.
- משתמש ששילם ולא קיבל premium — מתוקן אוטומטית (סנכרון מול Stripe + אותן נקודות כניסה כמו webhook).

### Webhook coverage

שלושה events במקום אחד:

| Event | התוצאה בדומיין |
|--------|-----------------|
| `checkout.session.completed` | מעבר ל־**SUCCEEDED** (כבעבר, עם idempotency) |
| `checkout.session.expired` | **CANCELED** |
| `payment_intent.payment_failed` | **FAILED** |

כל handler idempotent ברמת האירוע/תשלום.

### מטריקות

- `payments_failed_total` — **חי** (נקרא בנתיבי כשל).
- `payments_canceled_total` — חדש.
- `billing_reconciler_runs_total`, `billing_reconciler_recovered_total`, `billing_reconciler_errors_total`, `billing_idempotency_hits_total`.

פרט נוסף: [`docs/operations/MONITORING.md`](operations/MONITORING.md).

### Admin endpoints

- `GET /api/v1/admin/billing/stale-pending` — רשימת payments “תקועים” בהגדרות ה-reconciler + שדה JSON **`last_reconciler_run`** (מקביל ל־`BillingReconciler.last_run_at` בשרת).
- `POST /api/v1/admin/billing/reconcile/{payment_id}` — recovery ידני ל-payment בודד.

### migration 015 (revision `015_billing_idem`, קובץ `015_billing_idempotency_and_indexes.py`)

- טבלת `idempotency_keys`.
- partial index על `payments(status, created_at) WHERE status = 'pending'` — ביצועי reconciler בסקייל.

**הערת תפעול:** שני ה־15 במאגר מתמזגים ב־**`016_merge015_heads`**; ראו [`docs/architecture/DATABASE.md`](architecture/DATABASE.md).

### טסטים

**22 מקרי בדיקה** (JUnit-style; איסוף `pytest --collect-only` על ארבעת הקבצים להלן) — state machine, reconciler, שירות/webhook ו-idempotency API. כל עוד ההרצה ירוקה: **`uv run pytest`** על הקבצים האלה או הסוויטה המלאה.  
קבצים: `backend/tests/domain/test_billing_state_machine.py`, `backend/tests/domain/test_billing_reconciler.py`, `backend/tests/domain/test_billing.py`, `backend/tests/api/test_billing_idempotency.py`.

---

## קשר לפוסט על Kafka

| מה הפוסט אמר | מה עשינו |
|---|---|
| Idempotency Key | טבלה נפרדת, generic, עם fingerprint + `status_code` + תשובה מלאה |
| State Machine | `state_machine.py` עם `ALLOWED_TRANSITIONS` |
| Message Key / ordering | לא רלוונטי — Stripe הוא מקור האמת בזרימה הזו; כל payment/session נפרד |
| Kafka | לא הוספנו — ארכיטקטורה סינכרונית מתאימה לסקייל הנוכחי |

---

## מה מימשנו מעבר לפוסט

Reconciler עם advisory lock, Stripe Gateway adapter, שלושת ה-webhook events, admin observability, מטריקות מלאות.

---

## קישורים מהירים לתיעוד

| נושא | מסמך |
|------|------|
| API, כותרת `X-Idempotency-Key` ל-checkout | [`architecture/API.md`](architecture/API.md) |
| טבלאות ומיגרציות | [`architecture/DATABASE.md`](architecture/DATABASE.md) |
| משתני env (`BILLING_*`) | [`architecture/DEVELOPMENT.md`](architecture/DEVELOPMENT.md) |
| Prometheus | [`operations/MONITORING.md`](operations/MONITORING.md) |
| Why / Trade-offs מפורטים | [`FEATURE_DECISIONS.md` — billing-checkout-db-idempotency-reconciler](FEATURE_DECISIONS.md#billing-checkout-db-idempotency-reconciler) |
| ADR קצר | [`adr/ARCHITECTURE_DECISIONS_BACKEND.md` §26](adr/ARCHITECTURE_DECISIONS_BACKEND.md) |
| Highlights פורטפוליו | [`ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) |
