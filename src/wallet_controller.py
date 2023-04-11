import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from crypto import Crypto
from mongo import BaseMongoRepository
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from enum import Enum


class Status(Enum):
    CREATED = "created"
    PAID = "paid"


@dataclass
class Wallet:
    id: int
    keypair: Keypair
    pubkey: Pubkey


class WalletController(BaseMongoRepository):
    _collection_name = 'discord_users'
    _indexes = []

    def __init__(self):
        super().__init__()
        self.crypto = Crypto()

    async def mark_wallet_as_paid(self, user_id: str):
        logging.info(f'Marking user {user_id} as paid')
        await self._update_one({'_id': user_id},
                               {'$set': {'status': Status.PAID.value}},
                               upsert=False)

    async def get_wallet(self, user_id: str) -> Wallet:
        logging.info(f'Getting user {user_id}')
        user_dict = await self._find_one({'_id': user_id})
        if not user_dict:
            keypair = self.crypto.generate_keypair()
            await self._insert_one({
                '_id': user_id,
                'keypair': keypair.to_json(),
                'status': Status.CREATED.value,
                'timestamp_added': datetime.now(tz=timezone.utc),
            })
            user_dict = await self._find_one({'_id': user_id})

        keypair = Keypair.from_json(user_dict['keypair'])
        pubkey = keypair.pubkey()
        return Wallet(
            id=user_dict['_id'],
            keypair=keypair,
            pubkey=pubkey,
        )
