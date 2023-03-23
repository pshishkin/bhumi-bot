from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Optional
from bson import ObjectId
import settings
from mongo import BaseMongoRepository
from enum import Enum


class Status(Enum):
    PROCESSING = "processing"
    SUCCEED = "succeed"
    FAILED = "failed"


@dataclass
class VideoMix:
    id: ObjectId
    task_string: str
    status: Status
    status_details: Optional[str]
    output_file: Optional[str]
    timestamp_started: datetime
    timestamp_finished: Optional[datetime]


class VideoMixController(BaseMongoRepository):
    _collection_name = 'videos'
    _indexes = []

    def __init__(self):
        super().__init__()

    async def add_mix(self, task_string: str) -> ObjectId:
        obj_id = ObjectId()
        await self._insert_one({
            '_id': obj_id,
            'task_string': task_string,
            'status': Status.PROCESSING.value,
            'timestamp_started': datetime.now(tz=timezone.utc),
        })
        return obj_id

    async def get_mix(self, obj_id: str) -> VideoMix:
        mix = await self._find_one({'_id': ObjectId(obj_id)})
        return _get_video_mix_from_dict(mix)

    async def mark_mix_as_succeed(self, obj_id: str, output_file: str):
        await self._update_one({'_id': ObjectId(obj_id)}, {
            '$set': {
                'status': Status.SUCCEED.value,
                'output_file': output_file,
                'timestamp_finished': datetime.now(tz=timezone.utc),
            }
        })

    async def mark_mix_as_failed(self, obj_id: str, status_details: str):
        await self._update_one({'_id': ObjectId(obj_id)}, {
            '$set': {
                'status': Status.FAILED.value,
                'status_details': status_details,
                'timestamp_finished': datetime.now(tz=timezone.utc),
            }
        })


def _get_video_mix_from_dict(d: Dict) -> VideoMix:
    return VideoMix(
        id=d['_id'],
        task_string=d['task_string'],
        status=Status(d['status']),
        status_details=d.get('status_details'),
        output_file=d.get('output_file'),
        timestamp_started=d['timestamp_started'],
        timestamp_finished=d.get('timestamp_finished'),
    )
