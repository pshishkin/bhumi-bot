from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict

from bson import ObjectId

import settings
from mongo import BaseMongoRepository


@dataclass
class MappingResult:
    mapper_id: int
    result: str
    comment: str


@dataclass
class Photo:
    id: ObjectId
    photo_id: str
    user_id: int
    name: str
    mappings: List[MappingResult]


class PhotoController(BaseMongoRepository):
    _collection_name = 'photos'
    _indexes = []

    def __init__(self):
        super().__init__()

    async def add_photo(self, user_id: int, photo_id: str, person_name: str) -> ObjectId:
        obj_id = ObjectId()
        await self._insert_one({
            '_id': obj_id,
            'photo_id': photo_id,
            'user_id': user_id,
            'timestamp': datetime.now(tz=timezone.utc),
            'name': person_name,
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

    async def get_photo_by_id(self, obj_id: str) -> Photo:
        photo_dict = await self._find_one({'_id': ObjectId(obj_id)})
        return _get_photo_from_dict(photo_dict)

    async def get_photos_for_train(self) -> List[Photo]:
        ans = []
        async for photo_dict in self._find({'mappings.{}'.format(settings.TRAIN_USER_ID): {'$exists': True}}):
            ans.append(_get_photo_from_dict(photo_dict))
        return ans


def _get_photo_from_dict(d: Dict) -> Photo:
    return Photo(
        id=d['_id'],
        user_id=d['user_id'],
        photo_id=d['photo_id'],
        name=d['name'],
        mappings=[MappingResult(
            mapper_id=int(mapper_id),
            result=mapping['result'],
            comment=mapping.get('comment', None),
        ) for mapper_id, mapping in d['mappings'].items()]
    )