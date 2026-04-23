#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "== Redis Sentinel smoke test =="

docker compose exec -T redis-sentinel redis-cli -p 26379 sentinel get-master-addr-by-name mymaster >/tmp/sentinel-master.out
if ! rg -q "redis-primary|6379" /tmp/sentinel-master.out; then
  echo "❌ Sentinel does not report redis-primary:6379 as master"
  exit 1
fi

docker compose exec -T redis-sentinel redis-cli -p 26379 sentinel ckquorum mymaster >/tmp/sentinel-quorum.out
if ! rg -q "OK" /tmp/sentinel-quorum.out; then
  echo "❌ Sentinel quorum check failed"
  exit 1
fi

python - <<'PY'
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

from app.infrastructure.redis.broadcast import broadcast
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub
from app.infrastructure.redis.client import redis_client


async def main() -> None:
    await redis_client.connect()
    await redis_chat_pubsub.connect()
    await broadcast.connect()
    await redis_client.save("smoke:sentinel:cache", {"ok": True}, expire=30)
    got = await redis_client.get("smoke:sentinel:cache")
    if not got or not got.get("ok"):
        raise RuntimeError("redis_client read/write failed")
    await redis_chat_pubsub.publish("smoke:sentinel:chat", "ok")
    await broadcast.publish("smoke:sentinel:broadcast", "ok")
    await broadcast.disconnect()
    await redis_chat_pubsub.close()
    await redis_client.close()


asyncio.run(main())
PY

STATUS_CODE="$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health || true)"
if [[ "$STATUS_CODE" != "200" ]]; then
  echo "❌ Backend health endpoint is not 200 (got: $STATUS_CODE)"
  exit 1
fi

echo "✅ Redis Sentinel smoke test passed"
