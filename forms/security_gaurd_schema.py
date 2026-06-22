from forms.common import COMMON_FIELDS, ADDITIONAL_NOTES_FIELD

SECURITY_GUARD_FIELDS = COMMON_FIELDS + [
    {
        "key": "Day/Night Shift",
        "label": "Day/Night Shift",
        "type": "select",
        "options": ["Day", "Night", "Both"],
        "required": False,
    },
    {
        "key": "Residential/Commercial",
        "label": "Residential/Commercial",
        "type": "select",
        "options": ["Residential", "Commercial"],
        "required": False,
    },
    ADDITIONAL_NOTES_FIELD,
]

SERVICE_NAME = "Security Guard"