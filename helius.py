# Import necessary modules from the solana package
from solana.rpc.api import Client
from solana.rpc.api import Pubkey as PublicKey
import time

# Define the Solana RPC endpoint (choose devnet, testnet, or mainnet-beta as needed)
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# Initialize the client to interact with the Solana network
client = Client(SOLANA_RPC_URL)

# Define the token or account address for which transactions will be fetched
TOKEN_ADDRESS = ""  # Replace with the actual token address
pub_key = PublicKey.from_string(TOKEN_ADDRESS)


def get_all_signatures(client, pub_key, limit=12):
    """
    Fetch all transaction signatures for the given public key address.
    Implements pagination using the 'before' parameter.
    """
    signatures = []
    params = {"limit": limit}
    last_signature = None

    while True:
        if last_signature:
            params["before"] = last_signature

        # Fetch signatures in batch
        response = client.get_signatures_for_address(pub_key, **params)

        # If no further signatures are available, exit the loop
        print(response)

        batch = response.value

        # If no further signatures are available, exit the loop
        if not batch:
            break

        signatures.extend(batch)

        # Check if we have fetched fewer signatures than the limit; if yes, break the loop
        if len(batch) < limit:
            break

        # Update the last_signature variable for pagination
        last_signature = batch[-1].signature
        # Delay to avoid rate limiting
        time.sleep(5)

    return signatures


def get_transaction_details(client, signature):
    """
    Retrieve detailed transaction data using the transaction signature.
    """
    response = client.get_transaction(signature)
    if response.error is None:
        # Basic error handling
        print(f"Error fetching transaction {signature}: {response.error}")
        return None
    return response.value




def main():
    # Fetch all signatures for the specified token address
    signatures = get_all_signatures(client, pub_key)
    print(f"Total signatures fetched: {len(signatures)}")

    # For each signature, fetch transaction details
    transactions = []
    for idx, sig_info in enumerate(signatures):
        signature = sig_info.signature
        print(f"Fetching details for transaction [{idx + 1}/{len(signatures)}]: {signature}")
        tx_detail = get_transaction_details(client, signature)
        if tx_detail:
            transactions.append(tx_detail)
        time.sleep(0.2)

    print(f"Total transactions retrieved: {len(transactions)}")
    # Process or store the transactions as needed
    # For example, you can write them out to a JSON file:
    # import json
    # with open("transactions.json", "w") as outfile:
    #     json.dump(transactions, outfile, indent=2)


if __name__ == "__main__":
    main()
