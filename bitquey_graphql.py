import asyncio
import aiohttp

import winsound
import requests

from datetime import datetime, timedelta

from loguru import logger


class BitqueyGraphQL:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.endpoint = "https://streaming.bitquery.io/eap"
        self.token_url = "https://oauth2.bitquery.io/oauth2/token"
        self.access_token = self.get_access_token()
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

    def get_access_token(self):
        payload = (
            f'grant_type=client_credentials'
            f'&client_id={self.client_id}'
            f'&client_secret={self.client_secret}'
            f'&scope=api'
        )

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(self.token_url, headers=headers, data=payload)

        if response.status_code == 200:
            resp_json = response.json()
            return resp_json['access_token']
        else:
            logger.error(f"OAuth error: {response.status_code} - {response.text}")
            raise Exception("Failed to obtain access token")

    async def get_defi_activities(self):
        now = datetime.utcnow()
        since = (now - timedelta(seconds=30)).isoformat() + "Z"

        graphql_query = """
        query MyQuery {
          Solana {
            DEXTradeByTokens(
              where: {
                Trade: {
                  Currency: {
                    MintAddress: {is: "9gyfbPVwwZx4y1hotNSLcqXCQNpNqqz6ZRvo8yTLpump"}
                  },
                  AmountInUSD: {gt: "1000"}
                },
                Transaction: {
                  Result: {Success: true}
                },
                Block: {
                  Time: {since: "%s"}
                }
              },
              limit: {count: 10}
            ) {
              Trade {
                Currency {
                  MintAddress
                  Name
                  Symbol
                }
                Amount
                Price
              }
              Transaction {
                Signature
                Result {
                  Success
                }
              }
              Block {
                Time
              }
            }
          }
        }
        """ % since

        # Prepare the request payload
        payload = {
            "query": graphql_query
        }


        async with aiohttp.ClientSession() as session:
            async with session.post(self.endpoint, json=payload, headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    try:
                        # print(data)
                        return [
                            {
                                "tx_id": tx["Transaction"]["Signature"],
                                "amount": tx["Trade"]["Amount"],
                                #"price_usd": tx["Trade"]["PriceInUSD"],
                                "time": tx["Block"]["Time"]
                            }
                            for tx in data["data"]["Solana"]["DEXTradeByTokens"]
                        ]
                    except Exception as e:
                        logger.error(f"Parsing error: {e}")
                else:
                    logger.error(f"GraphQL error: {resp.status}")
        return []


class NotificationManager:
    @staticmethod
    async def send_notification(activity):
        winsound.Beep(1000, 1000)
        amount = float(activity['amount'])
        message = (
            f"🚨 Крупная транзакция обнаружена!\n"
            f"• TX: {activity['tx_id']}\n"
            f"• Сумма: {amount:,.0f} токенов\n"
            f"• Время: {activity['time']}"
        )
        logger.warning(message)


class Provider:
    def __init__(self):
        self.bitquey = BitqueyGraphQL(client_id="f6864b65-7cb1-43d6-a6d0-78ee8d913482", client_secret="91jT5d~WlWUyGjFTP.qN2MjBGC")
        self.notification_manager = NotificationManager()

    async def run_checking_activities(self):
        print("Monitoring started...")
        try:
            while True:
                activities = await self.bitquey.get_defi_activities()

                if activities:
                    for activity in activities:
                        await self.notification_manager.send_notification(activity)

                # await asyncio.sleep(3)

        except Exception as ex:
            logger.error(f"Critical Error: {ex}")


async def main():
    provider = Provider()
    await provider.run_checking_activities()


if __name__ == "__main__":
    asyncio.run(main())

#
# import asyncio
# from datetime import datetime, timedelta
#
# from gql import Client, gql
# from gql.transport.websockets import WebsocketsTransport
#
#
# async def main():
#     token = "ory_at_QkWjhMBbeXRXvdJpfhnpx2OOhhWvltl7UgTvl_CG5sM.dmfIVnE8Qz86j16YDwyycH9-P5RxRdZyfPCznLeBslI"
#
#     # WebSocket transport с протоколом graphql-ws
#     transport = WebsocketsTransport(
#         url=f"wss://streaming.bitquery.io/graphql?token={token}",
#         headers={"Sec-WebSocket-Protocol": "graphql-ws"}
#     )
#
#     # Подключение клиента
#     async with Client(transport=transport, fetch_schema_from_transport=False) as session:
#         now = datetime.utcnow()
#         thirty_seconds_ago = now - timedelta(seconds=30)
#
#         date_str = thirty_seconds_ago.strftime("%Y-%m-%d")
#         time_str = thirty_seconds_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
#         # Подписка на DEX-трейды по нужному токену
#         query = gql(f"""
#             subscription {{
#               EVM(network: bsc) {{
#                 DEXTrades(limit: {{count: 10}}, orderBy: {{}}) {{
#                   Trade {{
#                     Buy {{
#                       Currency {{
#                         SmartContract(selectWhere: {{is: "0xB7C0007ab75350c582d5eAb1862b872B5cF53F0C"}})
#                       }}
#                       Amount(selectWhere: {{gt: "100"}})
#                     }}
#                     Sell {{
#                       Amount(selectWhere: {{gt: "100"}})
#                     }}
#                   }}
#                   TransactionStatus {{
#                     Success
#                   }}
#                   Block {{
#                     Date(selectWhere: {{since: "{date_str}"}})
#                     Time(selectWhere: {{since: "{time_str}"}})
#                   }}
#                 }}
#               }}
#             }}
#         """)
#
#         # Получаем события в реальном времени
#         async for result in session.subscribe(query):
#             print("Новая транзакция:")
#             print(result)
#
#
# # Запуск
# asyncio.run(main())
