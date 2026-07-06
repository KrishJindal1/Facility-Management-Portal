from storage.excel_handler import find_latest_request_by_mobile
from utils.local_storage import save_request


def restore_request(mobile):
    """
    Restores the user's latest request from Excel
    into browser local storage.

    Returns:
        True  -> Request found
        False -> No request found
    """

    request = find_latest_request_by_mobile(mobile)

    if request is None:
        return False

    save_request(
        lead_id=request["Lead ID"],
        mobile=request["Mobile"],
        service=request["Service"],
    )

    return True