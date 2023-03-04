import logging

from motor.motor_asyncio import AsyncIOMotorClient

import settings

import logging
from typing import Any, Dict, List, Tuple

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCursor


class MongoConnection:
    client: AsyncIOMotorClient = None
    logger = logging.getLogger(__name__)

    def __init__(self):
        if not self.client:
            raise ConnectionError("Mongo client is not initialized")

    @classmethod
    def initialize(cls, **kwargs) -> None:

        if not cls.client:
            cls.client = AsyncIOMotorClient(
                settings.MONGO_CONN_STR,
                **kwargs
            )
            cls.logger.info('Created Mongo Client')
        else:
            cls.logger.info('Skipping more than once mongo client initialization')

    @classmethod
    def close_mongo_client(cls) -> None:
        if cls.client:
            cls.client.close()


class BaseMongoRepository:
    _collection_name: str
    _collection: AsyncIOMotorCollection
    _indexes: List[Tuple[str, Dict]] = []
    _logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()

    @classmethod
    async def initialize(cls):
        cls._logger.info('Initializing Mongo, db=%s, collection=%s', settings.MONGO_DATABASE, cls._collection_name)
        client = MongoConnection().client

        try:
            await client.server_info()
        except Exception:
            cls._logger.error("Unable to connect to Mongo")
            raise

        db = client[settings.MONGO_DATABASE]
        cls._collection = db[cls._collection_name]
        for index_name, index_params in cls._indexes:
            cls._logger.info('Creating Mongo index "%s" ON "%s" collection...',
                             index_name, cls._collection_name)
            await cls._collection.create_index(index_name, **index_params)

    async def _replace_one(self, *args, **kwargs) -> None:
        await self._collection.replace_one(*args, **kwargs)

    async def _insert_one(self, *args, **kwargs) -> None:
        await self._collection.insert_one(*args, **kwargs)

    async def _find_one(self, *args, **kwargs) -> Any:
        return await self._collection.find_one(*args, **kwargs)

    async def _delete_one(self, *args, **kwargs) -> None:
        await self._collection.delete_one(*args, **kwargs)

    async def _update_one(self, *args, **kwargs) -> None:
        await self._collection.update_one(*args, **kwargs)

    def _find(self, *args, **kwargs) -> AsyncIOMotorCursor:
        return self._collection.find(*args, **kwargs)
