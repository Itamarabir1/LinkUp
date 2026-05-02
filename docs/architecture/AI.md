# AI Architecture

תיעוד ממוקד לצינור **סיכום שיחות** לאחר סגירת conversation: אירועי Redis DB=1 → **`ai-worker`** → ניתוח → DB + התראות (Outbox) לפי הדומיין.

## Flow

### נתיב A — מתוזמן מתוך `task-worker` (מאומת בקוד)

1. משימת **`execute_chat_timeout_job`** (`app/workers/tasks/chat_timeout_task.py`) רצה מהלולאה המתוזמנת ב־`task_worker`.
2. לכל שיחה שעברה idle — קריאה **ישירה** (באותו תהליך) ל־`handle_conversation_completion` ב־`app/domain/chat/completion/service.py` עם `AsyncSession`.
3. השירות מריץ Groq דרך `app/domain/chat/ai/analyzer.py` / `client.py`, כותב ל־**`chat_analysis`**, ואז **`publish_to_outbox`** עם `chat.conversation.completed` (ראו [`EVENTS.md`](EVENTS.md)).

### נתיב B — מאזין Redis ל־`chat:completion:*` (subscriber בקוד)

1. `app/workers/ai_worker.py` מריץ `run_chat_completion_redis_listener` (`app/workers/tasks/chat_summary_task.py`) על **`REDIS_CHAT_URL`** (DB לוגי 1 במערכ המתוכנן).
2. Payload צפוי: JSON עם **`conversation_id`** + **`trigger_user_id`** → אותו `handle_conversation_completion`.

**דיוק תיעודי:** בשורות ה-Python הנסרקות ב־`backend/` אין כרגע מקור `publish` ברור לאותו ערוץ Redis (לעומת המאזין). **`REALTIME.md`** ו־**`chat-ws/*`** תואמו לנסח זאת במפורש; לפני שינוי מוצר הריצו `rg "chat:completion"` על כל הריפו.

## Observability / failure modes

- כשלי Groq או DB ב-worker לא חוסמים את זמן התגובה של ה-API בנתיב A (רץ מתוך worker).
- **לא** Celery — תזמון RabbitMQ דרך **`task-worker`** / `scheduled_tasks_queue`.

## Further reading

- [`docs/architecture/EVENTS.md`](EVENTS.md)
- [`docs/ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md)
- [`docs/DEPLOYMENT.md`](../DEPLOYMENT.md) (שירותי runtime כולל `ai-worker`)
