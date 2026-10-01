from datetime import datetime


class ValidationError(ValueError):
    pass


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

