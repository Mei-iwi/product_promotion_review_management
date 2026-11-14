from pymongo import MongoClient
from pymongo.database import Database
from flask import current_app, has_app_context

_client: MongoClient | None = None
_database: Database | None = None


def init_mongo(app, client=None) -> Database:
    global _client, _database
    if client is None and not app.config.get("MONGO_URI"):
        raise RuntimeError("Chưa cấu hình MONGO_URI trong môi trường hoặc file .env")
    _client = client or MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=3000)
    _database = _client[app.config["MONGO_DB"]]
    app.extensions["mongo_client"] = _client
    app.extensions["mongo_db"] = _database
    if not app.config.get("TESTING"):
        _client.admin.command("ping")
    return _database


def get_db() -> Database:
    if has_app_context():
        return current_app.extensions["mongo_db"]
    if _database is None:
        raise RuntimeError("MongoDB chưa được khởi tạo")
    return _database

