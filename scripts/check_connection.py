from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from config import Config
from pymongo import MongoClient

client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=3000)
client.admin.command("ping")
print(f"Kết nối MongoDB thành công: {Config.MONGO_DB}")

