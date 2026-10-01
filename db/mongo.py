from pymongo import MongoClient
from pymongo.database import Database

_client: MongoClient | None = None
_database: Database | None = None


def init_mongo(app, client=None) -> Database:
    global _client, _database
    _client = client or MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=3000)
    _database = _client[app.config["MONGO_DB"]]
    app.extensions["mongo_client"] = _client
    app.extensions["mongo_db"] = _database
    if not app.config.get("TESTING"):
        _client.admin.command("ping")
    return _database


def get_db() -> Database:
    if _database is None:
        raise RuntimeError("MongoDB chưa được khởi tạo")
    return _database

