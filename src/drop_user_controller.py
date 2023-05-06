from dataclasses import dataclass
from datetime import timezone, datetime

from mongo import BaseMongoRepository


@dataclass
class User:
    id: str
    claimed: int

class DropUserController(BaseMongoRepository):
    _collection_name = 'drop_users'
    _indexes = []

    def __init__(self):
        super().__init__()

    async def get_user(self, user_id: str) -> User:
        user_dict = await self._find_one({'_id': user_id})
        if not user_dict:
            return User(
                id=user_id,
                claimed=0,
            )
        claimed = sum([d['amount'] for d in user_dict['claims']])
        return User(
            id=user_dict['_id'],
            claimed=claimed,
        )

    async def get_total_claimed(self) -> int:
        total_claimed = 0
        async for user in self._find({}):
            total_claimed += sum([d['amount'] for d in user['claims']])
        return total_claimed

    async def add_claim(self, user_id: str, amount: int, wallet: str, ref: str) -> None:
        await self._update_one({'_id': user_id}, {'$push': {'claims': {
            'timestamp': datetime.now(tz=timezone.utc),
            'amount': amount,
            'wallet': wallet,
            'ref': ref,
        }}}, upsert=True)

