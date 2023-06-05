import asyncio
import logging
import enum
import json
from dataclasses import dataclass
from decimal import *
from typing import Any, List, Optional, Union
import base58

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
    get_associated_token_address,
    create_associated_token_account,
    transfer_checked,
    TransferCheckedParams,
)
from solders.system_program import TransferParams, transfer, create_account

import settings


class BalanceType(enum.Enum):
    CRYPTO = 2
    DB_STORAGE = 3

@dataclass
class Recipient:
    address: Pubkey
    share: Decimal

class Crypto:

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(logging.INFO)

        self.token_name = 'BHUMI'
        self.token_pubkey = Pubkey.from_string('FerpHzAK9neWr8Azn5U6qE4nRGkGU35fTPiCVVKr7yyF')

        self.decimals = 3
        self.airdrop_keypair: Keypair = Keypair.from_base58_string(settings.SOLANA_PRIVATE_KEY)
        self.daily_stash_keypair: Keypair = Keypair.from_base58_string(settings.SOLANA_DAILY_STASH_KEY)
        # self.receiver = self.daily_stash_keypair.pubkey()

        self.solana_cli = AsyncClient('https://api.mainnet-beta.solana.com')
        self.token = AsyncToken(self.solana_cli, self.token_pubkey, TOKEN_PROGRAM_ID,
                                self.airdrop_keypair)

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

    async def transfer_all_with_ratios(self, bhumi_from: Keypair, fees_from: Keypair, recipients: List[Recipient]) -> Optional[str]:
        self._logger.info(f'Sending bhumis from {bhumi_from.pubkey()} to {len(recipients)} recipients')
        shares_sum = Decimal(0)
        for recipient in recipients:
            shares_sum += recipient.share
        if shares_sum != Decimal(1):
            raise Exception('Share of sent bhumis not equal to 1')

        bhumis_to_send = await self.get_token_balance(bhumi_from.pubkey())
        await asyncio.sleep(1)
        if bhumis_to_send <= Decimal("0.1"):
            self._logger.info(f'Not enough BHUMI to send: {bhumis_to_send}, skipping transfer to {len(recipients)} recipients')
            return None

        txn = Transaction(fee_payer=fees_from.pubkey())
        for recipient in recipients:
            receiver = recipient.address
            associated_token_address = get_associated_token_address(receiver, self.token.pubkey)

            # Check if the associated token account exists
            token_account_info = await self.solana_cli.get_account_info(associated_token_address)

            if token_account_info is None or token_account_info.value is None:
                # Create associated token account if it does not exist
                create_associated_token_account_ix = create_associated_token_account(
                    bhumi_from.pubkey(),
                    receiver,
                    self.token.pubkey
                )
                txn.add(create_associated_token_account_ix)

            txn.add(
                transfer_checked(
                    TransferCheckedParams(
                        program_id=TOKEN_PROGRAM_ID,
                        source=get_associated_token_address(bhumi_from.pubkey(), self.token.pubkey),
                        mint=self.token.pubkey,
                        dest=associated_token_address,
                        owner=bhumi_from.pubkey(),
                        amount=int(bhumis_to_send * recipient.share * (10 ** self.decimals)),
                        decimals=self.decimals
                    )
                )
            )
        if bhumi_from != fees_from:
            signers = [bhumi_from, fees_from]
        else:
            signers = [bhumi_from]
        ans = await self.solana_cli.send_transaction(txn, *signers)
        self._logger.info(f"sent tx for {bhumis_to_send} bhumis to {len(recipients)} recipients")
        return base58.b58encode(bytearray(ans.value.to_bytes_array())).decode('utf-8')

    async def transfer_drop(self, receiver_str: str, token_balance_delta: Decimal, sol_balance_delta: Decimal) -> str:
        receiver = Pubkey.from_string(receiver_str)
        origin = self.airdrop_keypair
        txn = Transaction(fee_payer=origin.pubkey())
        associated_token_address = get_associated_token_address(receiver, self.token.pubkey)

        # Check if the associated token account exists
        token_account_info = await self.solana_cli.get_account_info(associated_token_address)

        if token_account_info is None or token_account_info.value is None:
            # Create associated token account if it does not exist
            create_associated_token_account_ix = create_associated_token_account(
                origin.pubkey(),
                receiver,
                self.token.pubkey
            )
            txn.add(create_associated_token_account_ix)

        txn.add(
            transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=get_associated_token_address(origin.pubkey(), self.token.pubkey),
                    mint=self.token.pubkey,
                    dest=associated_token_address,
                    owner=origin.pubkey(),
                    amount=int(token_balance_delta * (10 ** self.decimals)),
                    decimals=self.decimals
                )
            )
        )

        sol_transfer_amount = int(sol_balance_delta * (10 ** 9))  # Convert SOL to lamports
        txn.add(
            transfer(
                TransferParams(
                    from_pubkey=origin.pubkey(),
                    to_pubkey=receiver,
                    lamports=sol_transfer_amount
                )
            )
        )

        signers = [origin]
        ans = await self.solana_cli.send_transaction(txn, *signers)

        # return ans.get('result', None)
        return base58.b58encode(bytearray(ans.value.to_bytes_array())).decode('utf-8')
