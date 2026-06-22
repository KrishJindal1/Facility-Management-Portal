from forms.common import COMMON_FIELDS, ADDITIONAL_NOTES_FIELD

COOK_FIELDS = COMMON_FIELDS + [
    {"key": "Cuisine Type", "label": "Cuisine Type", "type": "text", "required": False},
    {
        "key": "Meals Per Day",
        "label": "Meals Per Day",
        "type": "number",
        "min": 1,
        "max": 5,
        "required": False,
    },
    ADDITIONAL_NOTES_FIELD,
]

SERVICE_NAME = "Cook"