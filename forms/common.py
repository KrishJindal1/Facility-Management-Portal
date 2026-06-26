COMMON_FIELDS = [
    {"key": "Name", "label": "Full Name", "type": "text", "required": True},
    {"key": "Mobile", "label": "Mobile Number", "type": "text", "max_chars": 10, "required": True},
    {"key": "Email", "label": "Email", "type": "text", "required": True},
    {"key": "Address", "label": "Address", "type": "text", "required": False},
    {"key": "City", "label": "City", "type": "text", "required": True},
    {"key": "State", "label": "State", "type": "text", "required": False},
    {"key": "Pincode", "label": "Pincode", "type": "text", "max_chars": 6, "required": False},
    {"key": "Start Date", "label": "Start Date", "type": "date", "required": False},
    {
        "key": "Preferred Timing",
        "label": "Preferred Timing",
        "type": "select",
        "options": ["Morning", "Afternoon", "Evening", "Full Day"],
        "required": False,
    },
    {"key": "Budget", "label": "Budget (₹/month)", "type": "number", "required": True},
]
 
ADDITIONAL_NOTES_FIELD = {
    "key": "Additional Notes", "label": "Additional Notes", "type": "textarea", "required": False
}