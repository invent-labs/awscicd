import os

import motor.motor_asyncio
import pymongo

client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])
db = client.foodsafety

users_collection = db["users"]
restaurants_collection = db["restaurants"]
circles_collection = db["circles"]
districts_collection = db['districts']
restaurants_type_collection = db['restaurants_type']
roles_collection = db["roles"]

# For non-async database connections only
pymongo_client = pymongo.MongoClient(os.environ["MONGODB_URL"],
                                     serverSelectionTimeoutMS=5000)
pymongo_db = pymongo_client['foodsafety']
users_collection_pymongo = pymongo_db["users"]
districts_collection_pymongo = pymongo_db['districts']
