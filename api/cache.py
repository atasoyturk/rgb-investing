import redis
import json
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

CACHE_TTL = 60 * 60 * 25  # 25 saat — bir sonraki güncellemeye kadar geçerli


def cache_key(market: str) -> str:
    return f"signals:{market}"


def get_cached_signals(market: str) -> dict | None:
    try:
        data = r.get(cache_key(market))
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"[Cache] GET error: {e}")
        return None


def set_cached_signals(market: str, signals: dict) -> None:
    try:
        r.setex(cache_key(market), CACHE_TTL, json.dumps(signals))
        print(f"[Cache] SET {market} — {len(signals.get('signals', []))} signals cached")
    except Exception as e:
        print(f"[Cache] SET error: {e}")


def invalidate_cache(market: str) -> None:
    try:
        r.delete(cache_key(market))
        print(f"[Cache] INVALIDATED {market}")
    except Exception as e:
        print(f"[Cache] DELETE error: {e}")