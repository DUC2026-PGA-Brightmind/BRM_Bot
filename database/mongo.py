"""
MongoDB async connection using Motor.
Always use this — never import pymongo directly.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import MONGO_URI, MONGO_DB

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            MONGO_URI,
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=10000,
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[MONGO_DB]
