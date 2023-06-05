import asyncio
import json
import logging
from decimal import Decimal
from asyncio import sleep
from typing import List

import requests
from solders.pubkey import Pubkey

import settings
from crypto import Crypto, Recipient

crypto = Crypto()
PRECISION = 1000000
logger = logging.getLogger(__name__)

E_WALLET_SHARE = Decimal('0.75')
NFT_WALLETS_SHARE = Decimal(1) - E_WALLET_SHARE

async def get_recipients() -> List[Recipient]:
    url = 'https://app.floppylabs.io/api/staked?key=DQHatxYRDAZce8irdohAo85n6WRCgqGN2SHWLY2ULRNJ'
    response = requests.get(url)

    # Raise an exception if the GET request is unsuccessful.
    if response.status_code != 200:
        raise Exception(f"GET request to {url} failed with status code {response.status_code}")

    # Load JSON data from the response
    data = json.loads(response.text)

    nft_per_wallet = {}
    nfts_total = 0
    for d in data:
        address = d['staker']
        nft_per_wallet[address] = nft_per_wallet.get(address, 0) + 1
        nfts_total += 1
    logger.info(f"found {nfts_total} NFTs on {len(nft_per_wallet)} addresses")

    ans = []
    dec_to_redistribute = Decimal(1)
    for w, v in nft_per_wallet.items():
        dec = Decimal(int(v * PRECISION / nfts_total)) / Decimal(PRECISION)
        ans.append(Recipient(
            address=Pubkey.from_string(w),
            share=dec * NFT_WALLETS_SHARE,
        ))

    ans.append(Recipient(
        address=Pubkey.from_string(settings.E_WALLET_PUBKEY),
        share=E_WALLET_SHARE,
    ))

    for w in ans:
        dec_to_redistribute -= w.share

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
    while True:
        await distribute()
        logger.info("sleeping for an hour...")
        await sleep(60 * 60)


def main_distribute_stash():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())
