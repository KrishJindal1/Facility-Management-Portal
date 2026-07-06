from streamlit_local_storage import LocalStorage

storage = LocalStorage()


def save_request(lead_id, mobile, service):
    """
    Save the user's latest request in browser local storage.
    """
    storage.setItem(
        "latest_request",
        {
            "lead_id": lead_id,
            "mobile": mobile,
            "service": service,
        },
    )


def get_request():
    """
    Get the latest stored request.
    Returns None if nothing is stored.
    """
    return storage.getItem("latest_request")


def delete_request():
    """
    Remove the stored request from browser local storage.
    """
    storage.removeItem("latest_request")


def has_request():
    """
    Returns True if a request exists.
    """
    return storage.getItem("latest_request") is not None