import asyncio
import logging
from decimal import Decimal
from asyncio import sleep
from typing import List

from solders.pubkey import Pubkey

from crypto import Crypto, Recipient

crypto = Crypto()
PRECISION = 1000000
logger = logging.getLogger(__name__)

async def get_recipients() -> List[Recipient]:

    nft_per_wallet = {}
    nfts_total = 0
    for d in data:
        nft_per_wallet[d.address] = nft_per_wallet.get(d.address, 0) + 1
        nfts_total += 1
    logger.info(f"found {nfts_total} NFTs on {len(nft_per_wallet)} addresses")

    ans = []
    dec_to_redistribute = Decimal(1)
    for w, v in nft_per_wallet.items():
        dec = Decimal(int(v * PRECISION / nfts_total)) / Decimal(PRECISION)
        dec_to_redistribute -= dec
        ans.append(Recipient(
            address=Pubkey.from_string(w),
            share=dec,
        ))

    if abs(dec_to_redistribute) > Decimal(0.0001):
        raise Exception('wrong distribution')

    ans[0].share += dec_to_redistribute

    return ans


async def distribute():
    logger.info("gathering info to distribute...")
    recipients = await get_recipients()

    logger.info("distributing...")
    await crypto.transfer_all_with_ratios(crypto.daily_stash_keypair, crypto.daily_stash_keypair, recipients)


async def async_main():
    await distribute()
    logger.info("sleeping for a day...")
    await sleep(60 * 60 * 24)


def main_distribute_stash():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())
