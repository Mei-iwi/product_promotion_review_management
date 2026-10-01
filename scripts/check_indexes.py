from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from config import Config
from db.indexes import inspect_indexes
from pymongo import MongoClient

db = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=3000)[Config.MONGO_DB]
has_missing = False
for collection, result in inspect_indexes(db).items():
    print(f"\n{collection}: {', '.join(result['actual'])}")
    if result["missing"]:
        has_missing = True
        print("  Thiếu:", ", ".join(result["missing"]))
print("\nKết quả:", "THIẾU INDEX" if has_missing else "ĐỦ INDEX")

