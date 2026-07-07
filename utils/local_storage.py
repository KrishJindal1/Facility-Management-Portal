from streamlit_local_storage import LocalStorage

storage = LocalStorage()


def save_request(lead_id, mobile, service):

    storage.setItem(
        "latest_request",
        {
            "lead_id": lead_id,
            "mobile": mobile,
            "service": service,
        },
    )


def get_request():

    data = storage.getItem("latest_request")

    if not data:
        return None

    return data


def delete_request():

    # Instead of removing the key, overwrite it with None.
    storage.setItem("latest_request", None)


def has_request():

    return get_request() is not None