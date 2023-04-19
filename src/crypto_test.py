import asyncio

from crypto import Crypto
from decimal import Decimal
import base58

async def main():
    crypto = Crypto()
    res = await crypto.transfer_drop('9GjrBqq4nVStvhN7xbP7NRwWfa5VwAL94D7hWkgcywdz', Decimal(1), Decimal('0.003'))
    print(res)
    # print(res.result.)
    # base58.b58encode_check(bytearray(res.value.to_bytes_array())).decode('utf-8')

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
