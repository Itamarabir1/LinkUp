#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

import aio_pika


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay messages from RabbitMQ DLQ back to main queues.")
    parser.add_argument(
        "--rabbitmq-url",
        default=os.getenv("RABBITMQ_URL", "amqp://admin:password123@localhost:5672/"),
        help="RabbitMQ connection URL",
    )
    parser.add_argument(
        "--queue",
        action="append",
        dest="queues",
        default=[],
        help="Base queue name (without .dlq). Can be passed multiple times.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum messages to replay per queue",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print current DLQ depth (no replay).",
    )
    return parser.parse_args()


def _default_queues() -> list[str]:
    # Mirrors current retry-enabled queues in QueueSpec.
    return ["notifications_queue", "avatar_upload_queue"]


async def _queue_depth(channel: aio_pika.abc.AbstractChannel, queue_name: str) -> int:
    queue = await channel.declare_queue(queue_name, durable=True, passive=True)
    result = getattr(queue, "declaration_result", None)
    message_count = getattr(result, "message_count", 0) if result else 0
    return int(message_count)


async def _replay_one_queue(
    channel: aio_pika.abc.AbstractChannel,
    base_queue: str,
    limit: int,
) -> dict[str, Any]:
    dlq_name = f"{base_queue}.dlq"
    queue = await channel.declare_queue(dlq_name, durable=True, passive=True)

    replayed = 0
    skipped = 0
    errors = 0

    for _ in range(limit):
        msg = await queue.get(fail=False)
        if msg is None:
            break
        try:
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=msg.body,
                    headers=dict(msg.headers or {}),
                    content_type=msg.content_type,
                    content_encoding=msg.content_encoding,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=base_queue,
            )
            await msg.ack()
            replayed += 1
        except Exception:
            await msg.nack(requeue=True)
            errors += 1
            break

    remaining = await _queue_depth(channel, dlq_name)
    return {
        "queue": base_queue,
        "dlq": dlq_name,
        "replayed": replayed,
        "skipped": skipped,
        "errors": errors,
        "remaining": remaining,
    }


async def main() -> None:
    args = _parse_args()
    queues = args.queues or _default_queues()
    queues = list(dict.fromkeys(queues))
    if args.limit <= 0:
        raise SystemExit("--limit must be > 0")

    connection = await aio_pika.connect_robust(args.rabbitmq_url, timeout=10)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=20)

    report: list[dict[str, Any]] = []
    try:
        if args.dry_run:
            for q in queues:
                dlq_name = f"{q}.dlq"
                depth = await _queue_depth(channel, dlq_name)
                report.append({"queue": q, "dlq": dlq_name, "depth": depth})
        else:
            for q in queues:
                item = await _replay_one_queue(channel, q, args.limit)
                report.append(item)
    finally:
        await connection.close()

    if args.dry_run:
        print("DLQ replay dry-run report")
        for item in report:
            print(f"- queue={item['queue']} dlq={item['dlq']} depth={item['depth']}")
        return

    print("DLQ replay report")
    print(json.dumps(report, ensure_ascii=True, indent=2))

    total_errors = sum(int(item.get("errors", 0)) for item in report)
    if total_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
