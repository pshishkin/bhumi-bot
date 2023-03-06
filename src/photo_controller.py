from datetime import datetime, timezone

from bson import ObjectId

from mongo import BaseMongoRepository


class PhotoController(BaseMongoRepository):
    _collection_name = 'photos'
    _indexes = []

    def __init__(self):
        super().__init__()

    async def add_photo(self, user_id: int, photo_id: str) -> ObjectId:
        obj_id = ObjectId()
        await self._insert_one({
            '_id': obj_id,
            'photo_id': photo_id,
            'user_id': user_id,
            'timestamp': datetime.now(tz=timezone.utc)
        })
        return obj_id

    async def get_photo_sender(self, obj_id: str) -> int:
        photo = await self._find_one({'_id': ObjectId(obj_id)})
        return photo['user_id']

    async def update_mapping_result(self, obj_id: str, mapper_id: int, result: str, comment: str = None):
        payload = {
            'timestamp': datetime.now(tz=timezone.utc),
            'result': result,
        }
        if comment:
            payload['comment'] = comment
        await self._update_one({'_id': ObjectId(obj_id)}, {
            '$set': {'mappings': {str(mapper_id): payload}}
        })
