import logging
from database.repository import generate_next_lead_id

logger = logging.getLogger(__name__)

PREFIX_MAP = {
    "Cook": "Cook",
    "Driver": "Driver",
    "Security Guard": "Security",
    "COOK": "Cook",
    "DRIVER": "Driver",
    "SECURITY_GUARD": "Security",
}


def generate_serial(service_name, organization_id=None):
    """
    Generates a sequential Lead / Requirement ID (e.g. Cook-001, Driver-001, Security-001).
    Primary source of truth is PostgreSQL.
    """
    try:
        return generate_next_lead_id(service_name, organization_id)
    except Exception as exc:
        logger.warning("Database serial generation failed: %s", exc)

    prefix = PREFIX_MAP.get(service_name, service_name.split()[0])
    return f"{prefix}-001"