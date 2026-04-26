"""Lua scripts for atomic Redis operations.

Loaded once at startup via redis-py's `register_script`, which transparently
caches via EVALSHA and falls back to EVAL on NOSCRIPT (after Sentinel failover
or FLUSHALL).
"""

from __future__ import annotations

from pathlib import Path

_LUA_DIR = Path(__file__).resolve().parent


def _read(name: str) -> str:
    return (_LUA_DIR / name).read_text(encoding="utf-8")


TOKEN_BUCKET_LUA: str = _read("token_bucket.lua")
SLIDING_WINDOW_LUA: str = _read("sliding_window.lua")

__all__ = ["TOKEN_BUCKET_LUA", "SLIDING_WINDOW_LUA"]
