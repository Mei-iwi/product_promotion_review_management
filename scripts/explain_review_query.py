from pathlib import Path
import pprint, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from config import Config
from pymongo import MongoClient

db = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=3000)[Config.MONGO_DB]
result = db.command("explain", {"find": "reviews", "filter": {"productCode": "SANPHAM2026090001", "rating": {"$gte": 4}}, "sort": {"createdAt": -1}}, verbosity="executionStats")
stats = result["executionStats"]
print("winningPlan:")
pprint.pp(result["queryPlanner"]["winningPlan"])
for key in ("totalDocsExamined", "totalKeysExamined", "executionTimeMillis"):
    print(f"{key}: {stats.get(key, 0)}")

