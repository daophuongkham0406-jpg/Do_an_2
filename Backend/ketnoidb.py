import os
import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["do_an_2"]

print("✅ Đã kết nối Database thành công (ketnoidb.py)!")