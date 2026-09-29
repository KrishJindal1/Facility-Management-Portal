"""
Browser local storage utility wrapper.
Uses streamlit_local_storage with lazy initialization for robust runtime and testing support.
"""
from typing import Optional, Dict, Any

_storage_instance = None


def _get_storage():
    """Lazily initializes the LocalStorage instance within Streamlit session context."""
    global _storage_instance
    if _storage_instance is None:
        try:
            from streamlit_local_storage import LocalStorage
            _storage_instance = LocalStorage()
        except Exception:
            return None
    return _storage_instance


def save_request(lead_id: str, mobile: str, service: str) -> None:
    storage = _get_storage()
    if storage is not None:
        try:
            storage.setItem(
                "latest_request",
                {
                    "lead_id": lead_id,
                    "mobile": mobile,
                    "service": service,
                },
            )
        except Exception:
            pass


def get_request() -> Optional[Dict[str, Any]]:
    storage = _get_storage()
    if storage is not None:
        try:
            data = storage.getItem("latest_request")
            if data:
                return data
        except Exception:
            pass
    return None


def delete_request() -> None:
    storage = _get_storage()
    if storage is not None:
        try:
            storage.setItem("latest_request", None)
        except Exception:
            pass


def has_request() -> bool:
    return get_request() is not None