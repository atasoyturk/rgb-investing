import os
from fastapi import Header, HTTPException


def _load_accepted_keys() -> set[str]:
    keys = {
        os.environ.get("INTERNAL_API_KEY_WEB"),
        os.environ.get("INTERNAL_API_KEY_AIRFLOW"),
    }
    return {k for k in keys if k}


def verify_internal_api_key(x_internal_api_key: str | None = Header(default=None)) -> None:
    accepted = _load_accepted_keys()
    if not accepted:
        return
    if x_internal_api_key not in accepted:
        raise HTTPException(status_code=401, detail="Missing or invalid internal API key")