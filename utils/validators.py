import re

EMAIL_PATTERN = r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$"


def validate_name(name):
    if not name or not name.strip():
        return False, "Name is required."
    return True, ""


def validate_mobile(mobile):
    mobile = str(mobile).strip()
    if not mobile:
        return False, "Mobile number is required."
    if not mobile.isdigit():
        return False, "Mobile number must contain digits only."
    if len(mobile) != 10:
        return False, "Mobile number must be exactly 10 digits."
    return True, ""


def validate_email(email):
    email = email.strip()
    if not email:
        return False, "Email is required."
    if not re.match(EMAIL_PATTERN, email):
        return False, "Enter a valid email address."
    return True, ""


def validate_city(city):
    if not city or not city.strip():
        return False, "City is required."
    return True, ""


def validate_budget(budget):
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        return False, "Budget must be a number."
    if budget <= 0:
        return False, "Budget must be a positive value."
    return True, ""

def validate_pincode(pincode):
    pincode = str(pincode).strip()

    if not pincode:
        return True, ""      # Optional field

    if not pincode.isdigit():
        return False, "Pincode must contain digits only."

    if len(pincode) != 6:
        return False, "Pincode must be exactly 6 digits."

    return True, ""

def validate_form(data, required_fields=("Name", "Mobile", "Email", "City", "Budget")):
    """
    Runs all relevant validators against a lead_data dict and returns
    a list of error messages. Empty list means the form is valid.

    Only validates fields present in `required_fields`, so forms that
    don't need email (if you ever add one) can skip it.
    """
    errors = []

    checks = {
        "Name": validate_name,
        "Mobile": validate_mobile,
        "Email": validate_email,
        "City": validate_city,
        "Budget": validate_budget,
        "Pincode": validate_pincode,
    }

    for field in required_fields:
        validator = checks.get(field)
        if not validator:
            continue
        is_valid, message = validator(data.get(field, ""))
        if not is_valid:
            errors.append(message)

    return errors