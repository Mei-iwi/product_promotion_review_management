from datetime import datetime
import math


class ValidationError(ValueError):
    pass


def whitelist(data, fields, object_fields=(), list_fields=(), number_fields=()):
    if not isinstance(data, dict) or set(data) - set(fields):
        raise ValidationError('Trường dữ liệu không được phép')
    from services.security import validate_input
    validate_input(data)
    for key, value in data.items():
        if key in object_fields:
            valid = isinstance(value, dict)
        elif key in list_fields:
            valid = isinstance(value, list) and all(isinstance(item, str) for item in value)
        elif key in number_fields:
            try:
                valid = not isinstance(value, (bool, dict, list)) and math.isfinite(float(value))
            except (ValueError, TypeError, OverflowError):
                valid = False
        elif isinstance(value, datetime):
            valid = key in {'joinedAt', 'startDate', 'endDate'}
        else:
            valid = isinstance(value, str)
        if not valid:
            raise ValidationError('Kiểu dữ liệu không hợp lệ: ' + key)
    return data


def required(data, names):
    missing = [name for name in names if data.get(name) in (None, "")]
    if missing:
        raise ValidationError("Thiếu trường bắt buộc: " + ", ".join(missing))


def parse_date(value, field):
    if isinstance(value, datetime): return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} không đúng định dạng ngày") from exc

