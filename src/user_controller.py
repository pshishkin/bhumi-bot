from mongo import BaseMongoRepository


class UserController(BaseMongoRepository):
    _collection_name = 'users'
    _indexes = []

    def __init__(self):
        super().__init__()

    async def get_user(self, user_id: int) -> dict:
        return await self._find_one({'_id': user_id})

    async def update_name(self, user_id: int, name: str):
        await self._update_one({'_id': user_id}, {'$set': {'name': name}}, upsert=True)

    async def update_mapping_request_subscription(self, user_id: int, subscribed_to_mapping_requests: bool):
        await self._update_one({'_id': user_id},
                               {'$set': {'subscribed_to_mapping_requests': subscribed_to_mapping_requests}},
                               upsert=True)

    async def get_users_subscribed_to_mapping_requests(self) -> list[int]:
        return [user['_id'] async for user in self._find({'subscribed_to_mapping_requests': True})]
