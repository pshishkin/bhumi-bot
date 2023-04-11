import logging
import enum
import json
from decimal import *

from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
# from solana.transaction import Transaction, TransactionInstruction, AccountMeta
from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
from solana.rpc.types import TxOpts

from solana.transaction import Transaction
from spl.token.instructions import (
    initialize_mint,
    InitializeMintParams,
    initialize_account,
    InitializeAccountParams,
    mint_to_checked,
    MintToCheckedParams,
    get_associated_token_address,
    create_associated_token_account,
    transfer_checked,
    TransferCheckedParams,
)

import settings


class BalanceType(enum.Enum):
    CRYPTO = 2
    DB_STORAGE = 3


class Crypto:

    def __init__(self):
        self.token_name = 'BHUMI'
        self.token_pubkey = Pubkey.from_string('FerpHzAK9neWr8Azn5U6qE4nRGkGU35fTPiCVVKr7yyF')

        self.decimals = 3
        self.fee_payer_keypair: Keypair = Keypair.from_base58_string(settings.SOLANA_PRIVATE_KEY)
        self.receiver = self.fee_payer_keypair.pubkey()

        self.solana_cli = AsyncClient('https://api.mainnet-beta.solana.com')
        self.token = AsyncToken(self.solana_cli, self.token_pubkey, TOKEN_PROGRAM_ID,
                                self.fee_payer_keypair)

    def generate_keypair(self) -> Keypair:
        kp = Keypair()
        return kp

    async def get_token_balance(self, pubkey: Pubkey) -> Decimal:
        ans = await self.token.get_accounts_by_owner(pubkey)
        if not ans.value:
            return Decimal(0)
        # print(ans)
        token_account = ans.value[0]
        # print(token_account)
        balance = await self.token.get_balance(token_account.pubkey)
        # print(balance.value)
        value = balance.value
        # print(value.decimals, value.amount)
        return Decimal(value.amount) / (Decimal(10) ** value.decimals)

    async def init_balance(self, user):
        if self.balance_type == BalanceType.DB_STORAGE:
            user.balance = user.balance_dev
        else:
            user.balance = await self._get_token_balance(user.keypair)

    async def _charge_token(self, kp_from: Keypair, balance_delta: Decimal) -> str:
        txn = Transaction(fee_payer=self.fee_payer_keypair.public_key)

        for recipient_public_key, share in self._recipients:
            self._logger.info(f'Adding to transaction:')
            self._logger.info(f'Adding to transaction: program_id={TOKEN_PROGRAM_ID}')
            self._logger.info(
                f'Adding to transaction: source={get_associated_token_address(kp_from.public_key, self.token.pubkey)}')
            self._logger.info(f'Adding to transaction: mint={self.token.pubkey}')
            self._logger.info(f'DBG: dest_associated_owner={recipient_public_key}')
            self._logger.info(
                f'Adding to transaction: dest={get_associated_token_address(recipient_public_key, self.token.pubkey)}')
            self._logger.info(f'Adding to transaction: owner={kp_from.public_key}')
            self._logger.info(f'Adding to transaction: amount={int(balance_delta * (10 ** self.decimals) * share)}')
            self._logger.info(f'Adding to transaction: decimals={self.decimals}')

            txn.add(
                transfer_checked(
                    TransferCheckedParams(
                        program_id=TOKEN_PROGRAM_ID,
                        source=get_associated_token_address(kp_from.public_key, self.token.pubkey),
                        mint=self.token.pubkey,
                        dest=get_associated_token_address(recipient_public_key, self.token.pubkey),
                        owner=kp_from.public_key,
                        amount=int(balance_delta * (10 ** self.decimals) * share),
                        decimals=self.decimals
                    )
                )
            )

        signers = [self.fee_payer_keypair, kp_from]
        ans = await self.solana_cli.send_transaction(txn, *signers)

        return ans.get('result', None)

    def sub_balance(self, user, balance_delta: Decimal, sess) -> str:
        if self.balance_type == BalanceType.DB_STORAGE:
            user.balance_dev -= balance_delta
            user.balance = user.balance_dev
            sess.add(user)
            return True
        else:
            tx_hash = self._charge_token(user.keypair, balance_delta)
            if tx_hash:
                user.balance -= balance_delta
                return tx_hash
            else:
                return None

    def set_balance(self, user, new_balance: Decimal, sess) -> bool:
        if self.balance_type == BalanceType.DB_STORAGE:
            user.balance = user.balance_dev = new_balance
            sess.add(user)
            return True
        else:
            return False