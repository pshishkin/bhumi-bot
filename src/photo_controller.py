from bson import ObjectId

from mongo import BaseMongoRepository


class PhotoController(BaseMongoRepository):
    _collection_name = 'photos'
    _indexes = []

    def __init__(self):
        super().__init__()

    async def add_photo(self, user_id: int, photo_id: str) -> ObjectId:
        obj_id = ObjectId()
        await self._insert_one({'_id': obj_id, 'photo_id': photo_id})
        return obj_id

