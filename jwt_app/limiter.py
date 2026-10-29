import time
from contextlib import contextmanager

from fastapi import HTTPException, Request
from limits import parse
from limits.storage import RedisStorage
from limits.strategies import MovingWindowRateLimiter
from redis.exceptions import RedisError
from slowapi.util import get_remote_address

# only failed logins count, 5 wrong tries in 1 minute -> locked out
FAILED_LOGIN_LIMIT = parse("5/minute")

# counts live in Redis, so a lockout survives a backend restart;
# short timeouts so a dead Redis fails fast instead of hanging the login
failed_logins = MovingWindowRateLimiter(
    RedisStorage("redis://localhost:6379", socket_connect_timeout=2, socket_timeout=2)
)


@contextmanager
def redis_errors():
    # without Redis we can't tell who is locked out, so refuse logins instead of allowing all
    try:
        yield
    except RedisError:
        raise HTTPException(status_code=503, detail="Login is unavailable: can't reach Redis")


def check_not_locked(request: Request):
    key = get_remote_address(request)
    with redis_errors():
        if failed_logins.test(FAILED_LOGIN_LIMIT, key):
            return
        reset_time, _ = failed_logins.get_window_stats(FAILED_LOGIN_LIMIT, key)

    wait = max(1, int(reset_time - time.time()))
    raise HTTPException(
        status_code=429,
        detail=f"Too many failed login attempts. Try again in {wait} seconds.",
        headers={"Retry-After": str(wait)},
    )


def record_failed_login(request: Request):
    with redis_errors():
        failed_logins.hit(FAILED_LOGIN_LIMIT, get_remote_address(request))


def reset_failed_logins(request: Request):
    with redis_errors():
        failed_logins.clear(FAILED_LOGIN_LIMIT, get_remote_address(request))
