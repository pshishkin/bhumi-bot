import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solana.transaction import Transaction

# Replace this with the desired Solana address
# ADDRESS = "GwGzxKxeJgvyhi1QNuqWoqE1yTBwAJn84rfDsuCQjPKJ"
ADDRESS = "E3eKSe9Cd2uKLzm6hpPo1sZe3rjnLNTEsf35eMsJsfee"

async def main():
    # Connect to Solana devnet
    solana_client = AsyncClient("https://api.mainnet-beta.solana.com")

    # Convert the address string to a PublicKey object
    pubkey = Pubkey.from_string(ADDRESS)

    # Fetch the recent transactions
    response = await solana_client.get_signatures_for_address(pubkey, limit=5)

    if not response:
        print("No recent transactions found for this address.")
        return

    # print(dir(response))
    print(response.value)

    # Print transaction logs
    for tx_data in response.value:
        print(f"Transaction Signature: {tx_data.signature}")

        # Get transaction details
        tx_response = await solana_client.get_transaction(tx_data.signature)
        if not tx_response:
            print("Unable to fetch transaction details.")
            continue

        print(tx_response)
        tx_response = tx_response.value.transaction
        print(tx_response.transaction)
        print(tx_response.meta)
        print(tx_response.meta.log_messages)


        # Deserialize the transaction
        transaction = Transaction.from_bytes(tx_response['transaction']['message']['instructions'])
        print("Transaction Instructions:")
        for instruction in transaction.instructions:
            print(f"  - {instruction}")

        # Print logs
        print("Transaction Logs:")
        for log in tx_response['meta']['logMessages']:
            print(f"  - {log}")

        print("\n")

# Run the async function
asyncio.run(main())
