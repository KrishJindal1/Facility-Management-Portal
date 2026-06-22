from forms.common import COMMON_FIELDS, ADDITIONAL_NOTES_FIELD

DRIVER_FIELDS = COMMON_FIELDS + [
    {"key": "Vehicle Type", "label": "Vehicle Type", "type": "text", "required": False},
    {
        "key": "License Required",
        "label": "License Required",
        "type": "select",
        "options": ["Yes", "No"],
        "required": False,
    },
    ADDITIONAL_NOTES_FIELD,
]

SERVICE_NAME = "Driver"