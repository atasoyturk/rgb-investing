import redis
import json
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

CACHE_TTL = 60 * 60 * 24 * 8  # 8 days, to ensure signals are refreshed weekly


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


def get_cached_gradcam(market: str, ticker: str):
    try:
        data = r.get(f"gradcam:{market}:{ticker}")
        if data:
            import base64
            return base64.b64decode(data)
        return None
    except Exception as e:
        print(f"[Cache] Gradcam GET error: {e}")
        return None

def set_cached_gradcam(market: str, ticker: str, png_bytes: bytes) -> None:
    try:
        import base64
        r.setex(f"gradcam:{market}:{ticker}", CACHE_TTL, base64.b64encode(png_bytes).decode())
    except Exception as e:
        print(f"[Cache] Gradcam SET error: {e}")