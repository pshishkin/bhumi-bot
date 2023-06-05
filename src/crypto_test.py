import asyncio
import logging

from crypto import Crypto, Recipient
from decimal import Decimal
import base58

from mongo import MongoConnection
from wallet_controller import WalletController


async def main():
    MongoConnection.initialize()
    await WalletController.initialize()
    crypto = Crypto()
    wallet_controller = WalletController()

    wallets = await wallet_controller.get_all_wallets()

    for w in wallets[2:7]:
        res = await crypto.transfer_all_with_ratios(
            w.keypair,
            crypto.daily_stash_keypair,
            [Recipient(address=crypto.daily_stash_keypair.pubkey(), share=Decimal(1))],
        )
        print(f'tx hash {res}')
        await asyncio.sleep(10)

async def main2():
    crypto = Crypto()
    res = await crypto.transfer_drop('9GjrBqq4nVStvhN7xbP7NRwWfa5VwAL94D7hWkgcywdz', Decimal(1), Decimal('0.003'))
    print(res)
    # print(res.result.)
    # base58.b58encode_check(bytearray(res.value.to_bytes_array())).decode('utf-8')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
