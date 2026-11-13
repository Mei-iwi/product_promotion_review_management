from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from config import Config
from pymongo import MongoClient

client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=3000)
collections = ["products", "promotions", "customers", "reviews", "orders"]
client.admin.command("ping")
database = client[Config.MONGO_DB]

print(f"Database: {Config.MONGO_DB}")
print(f"{'Collection':<15}{'Số document':>15}")
for name in collections:
    count = database[name].count_documents({})
    print(f"{name:<15}{count:>15}")

