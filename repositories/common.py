from bson import ObjectId
from bson.decimal128 import Decimal128
from datetime import date, datetime


def serialize(value):
    if isinstance(value, (ObjectId, Decimal128)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items() if key != "_id"}
    return value

