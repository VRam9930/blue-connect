from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["blue_connect"]

jobs_collection = db["jobs"]
users_collection = db["users"]
applications_collection = db["applications"]

