-- Sliding-window log atomic rate limiter (anti-bruteforce friendly: no burst).
-- KEYS[1] = sorted-set key (members are unique request ids, scores are timestamps in ms)
-- ARGV[1] = window_ms
-- ARGV[2] = max_count
-- ARGV[3] = now_ms
-- ARGV[4] = member (unique per request, e.g. uuid4 hex; avoids ZADD overwrites)
--
-- Returns: {allowed, max_count, remaining, retry_after_ms}
-- retry_after_ms is derived from the oldest entry still inside the window:
--   retry_after = oldest_score + window - now
-- Once that entry ages out, a slot becomes available.

local key = KEYS[1]
local win = tonumber(ARGV[1])
local maxn = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, 0, now - win)
local count = redis.call('ZCARD', key)
local allowed = 0
local retry_after_ms = 0

if count < maxn then
    redis.call('ZADD', key, now, member)
    allowed = 1
    count = count + 1
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    if #oldest >= 2 then
        retry_after_ms = math.max(0, tonumber(oldest[2]) + win - now)
    end
end

redis.call('PEXPIRE', key, win + 1000)

return {allowed, maxn, math.max(0, maxn - count), retry_after_ms}
