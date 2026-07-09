from flask import jsonify


def require_fields(data, *fields):
    """Return (data, None) if all fields present; (None, error_response) if body missing or field absent."""
    if not data:
        return None, (jsonify({"error": "Request body required"}), 400)
    missing = [f for f in fields if data.get(f) is None]
    if missing:
        return None, (jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400)
    return data, None


def coerce_int(value, field_name):
    """Return (int_value, None) or (None, error_response) on non-numeric input."""
    try:
        return int(value), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": f"Field '{field_name}' must be an integer"}), 400)
