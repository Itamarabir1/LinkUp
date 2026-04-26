-- Token Bucket atomic rate limiter.
-- KEYS[1] = bucket key (hash with fields: tokens, ts)
-- ARGV[1] = capacity (max tokens)
-- ARGV[2] = refill_per_sec (tokens added per second; can be fractional)
-- ARGV[3] = now_ms (caller-supplied wall clock; trades NTP-bounded drift for replication safety)
-- ARGV[4] = requested (tokens to consume; default 1)
--
-- Returns: {allowed, capacity, remaining_floor, retry_after_ms}
-- allowed: 1 if granted, 0 if rejected (fail-closed inside Lua; caller may fail-open on Redis errors).
-- retry_after_ms: how long until enough tokens accrue (0 when allowed).
--
-- Notes:
-- * HSET (variadic) is used over deprecated HMSET (Redis 4.0+).
-- * PEXPIRE is sized to (capacity / refill) ms + 1s to keep idle keys alive long enough
--   for refill math to be meaningful, but expire eventually to bound memory.
-- * Float precision is acceptable for rate limiting; we explicitly accept Lua 5.1 number semantics.

local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4]) or 1

local s = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(s[1])
local ts = tonumber(s[2])
if tokens == nil then
    tokens = capacity
    ts = now
end

local elapsed = math.max(0, now - ts) / 1000.0
tokens = math.min(capacity, tokens + elapsed * refill)

local allowed = 0
local retry_after_ms = 0
if tokens >= requested then
    tokens = tokens - requested
    allowed = 1
else
    retry_after_ms = math.ceil(((requested - tokens) / refill) * 1000)
end

redis.call('HSET', key, 'tokens', tokens, 'ts', now)
redis.call('PEXPIRE', key, math.ceil((capacity / refill) * 1000) + 1000)

return {allowed, capacity, math.floor(tokens), retry_after_ms}
