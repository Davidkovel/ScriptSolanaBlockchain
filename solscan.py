import aiohttp
import asyncio
from typing import Dict, List, Optional

from loguru import logger


class SolscanBlockchain:
    def __init__(self):
        self.api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3NDM4NzM0ODU5MTcsImVtYWlsIjoiZGtvdmVsN0BnbWFpbC5jb20iLCJhY3Rpb24iOiJ0b2tlbi1hcGkiLCJhcGlWZXJzaW9uIjoidjIiLCJpYXQiOjE3NDM4NzM0ODV9.6ANfd62R9A39WcI9Bpg5B1AIEXh_fdQRwKIaK0p-pug"
        self.base_url = "https://pro-api.solscan.io/v2.0/"
        self.session = aiohttp.ClientSession()
        self.headers = {"token": self.api_key}
        self.target_token = ""
        self.threshold_amount = 4000
        self.seen_tx_ids = set()

    async def get_defi_activities(self) -> Optional[List[Dict]]:
        """Получаем DeFi активности по токену"""
        url = f"{self.base_url}token/defi/activities"
        params = {
            "address": self.target_token,
            "page": 1,
            "page_size": 20,
            "sort_by": "block_time",
            "sort_order": "desc"
        }
        try:
            async with self.session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return await self.deserialize(data)
                else:
                    logger.error(f"API Error: {response.status}, {await response.text()}")
                    return None
        except Exception as e:
            print(f"Connection Error: {e}")
            return None

    async def deserialize(self, data: Dict) -> List[Dict]:
        """Парсим и фильтруем данные"""
        filtered_activities = []

        for activity in data.get("data", []):
            try:
                tx_id = activity["trans_id"]
                # print(f"Processing tx_id: {tx_id}")
                if tx_id in self.seen_tx_ids:
                    continue

                if activity["activity_type"] == "ACTIVITY_AGG_TOKEN_SWAP":
                    routers = activity["routers"]

                    # Определяем в какой части swap наш токен (input или output)
                    if routers["token1"] == self.target_token:
                        amount = float(routers["amount1"])
                        token_in = routers["token1"]
                        token_out = routers["token2"]
                    elif routers["token2"] == self.target_token:
                        amount = float(routers["amount2"])
                        token_in = routers["token2"]
                        token_out = routers["token1"]
                    else:
                        continue

                    # Конвертируем amount с учетом decimals
                    decimals = routers["token1_decimals"] if routers["token1"] == self.target_token else routers[
                        "token2_decimals"]
                    normalized_amount = amount / (10 ** decimals)

                    # Фильтруем по пороговому значению
                    if await self.filter_check_amount(normalized_amount):
                        activity_data = {
                            "tx_id": activity["trans_id"],
                            "block_time": activity["block_time"],
                            "from_address": activity["from_address"],
                            "amount": normalized_amount,
                            "token_in": token_in,
                            "token_out": token_out,
                            "platform": activity["platform"]
                        }
                        filtered_activities.append(activity_data)
                        self.seen_tx_ids.add(tx_id)

            except Exception as e:
                logger.error(f"Error parsing activity: {e}")

        return filtered_activities

    async def filter_check_amount(self, amount: float) -> bool:
        """Проверяем превышение порогового значения"""
        return amount >= self.threshold_amount

    async def close(self):
        await self.session.close()


class NotificationManager:
    @staticmethod
    async def send_notification(activity: Dict):

        message = (
            f"🚨 Крупная транзакция обнаружена!\n"
            f"• TX: {activity['tx_id']}\n"
            f"• Сумма: {activity['amount']:,.0f} токенов\n"
            f"• Обмен: {activity['token_in']} → {activity['token_out']}\n"
            f"• Адрес: {activity['from_address']}\n"
            f"• Время: {activity['block_time']}\n"
            f"• Платформа: {activity['platform']}"
        )
        logger.info(message)


class Provider:
    def __init__(self):
        self.solscan = SolscanBlockchain()
        self.last_checked_block = None
        self.notification_manager = NotificationManager()

    async def run_checking_activities(self):
        try:
            print("Prod started")
            while True:
                # print("Проверяем новые активности...")
                activities = await self.solscan.get_defi_activities()

                if activities:
                    for activity in activities:
                        await self.notification_manager.send_notification(activity)

                await asyncio.sleep(1)

        except Exception as ex:
            logger.error(f"Critical Error: {ex}")
        finally:
            await self.solscan.close()


async def main():
    provider = Provider()
    await provider.run_checking_activities()


if __name__ == "__main__":
    # logger.add("file.log", level="DEBUG", colorize=False, backtrace=True, diagnose=True)
    # logger.remove(0)
    asyncio.run(main())
