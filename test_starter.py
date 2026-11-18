"""Тесты recommend_price. Запуск: python -m unittest -v"""

import asyncio
import unittest
from decimal import Decimal

from starter import recommend_price, sample_fetch_offers


def source(offers, status="success"):
    async def fetch():
        return {"status": status, "offers": offers}
    return fetch


def offer(price, seller="PARTS", days=3):
    return {"seller": seller, "price": Decimal(price), "delivery_days": days}


class RecommendPriceTest(unittest.IsolatedAsyncioTestCase):
    async def test_sample_from_task(self):
        res = await recommend_price(sample_fetch_offers, Decimal("4900.00"), Decimal("4500.00"))
        self.assertEqual(res["price"], Decimal("4728.00"))
        self.assertIsInstance(res["price"], Decimal)
        self.assertEqual(res["decision"], "APPLY")

    async def test_timeout_returns_hold(self):
        async def slow():
            await asyncio.sleep(10)
        res = await recommend_price(slow, Decimal("1000.00"), Decimal("500.00"), timeout_s=0.05)
        self.assertEqual((res["price"], res["decision"]), (Decimal("1000.00"), "HOLD"))

    async def test_source_exception_returns_hold(self):
        async def broken():
            raise ConnectionError("down")
        res = await recommend_price(broken, Decimal("1000.00"), Decimal("500.00"))
        self.assertEqual((res["price"], res["decision"]), (Decimal("1000.00"), "HOLD"))

    async def test_partial_status_returns_hold(self):
        res = await recommend_price(source([offer("900.00")], status="partial"),
                                    Decimal("1000.00"), Decimal("500.00"))
        self.assertEqual((res["price"], res["decision"]), (Decimal("1000.00"), "HOLD"))

    async def test_no_suitable_offers_keeps_price_below_min(self):
        offers = [offer("900.00", seller="MyShop"), offer("800.00", days=None), offer("700.00", days=7)]
        res = await recommend_price(source(offers), Decimal("400.00"), Decimal("500.00"))
        self.assertEqual((res["price"], res["decision"]), (Decimal("400.00"), "HOLD"))

    async def test_rounds_down_to_kopeck(self):
        # 1000.99 * 0.985 = 985.97515 -> 985.97 (обычное округление дало бы 985.98)
        res = await recommend_price(source([offer("1000.99")]), Decimal("1000.00"), Decimal("1.00"))
        self.assertEqual((res["price"], res["decision"]), (Decimal("985.97"), "APPLY"))

    async def test_min_price_floor(self):
        res = await recommend_price(source([offer("900.00")]), Decimal("1000.00"), Decimal("950.00"))
        self.assertEqual((res["price"], res["decision"]), (Decimal("950.00"), "APPLY"))

    async def test_exactly_30_percent_is_apply(self):
        # 710.66 * 0.985 = 700.0001 -> 700.00, ровно −30% от 1000
        res = await recommend_price(source([offer("710.66")]), Decimal("1000.00"), Decimal("1.00"))
        self.assertEqual((res["price"], res["decision"]), (Decimal("700.00"), "APPLY"))

    async def test_more_than_30_percent_is_review(self):
        # 710.65 * 0.985 = 699.99025 -> 699.99, чуть больше −30%
        res = await recommend_price(source([offer("710.65")]), Decimal("1000.00"), Decimal("1.00"))
        self.assertEqual((res["price"], res["decision"]), (Decimal("699.99"), "REVIEW"))

    async def test_raise_over_30_percent_is_review(self):
        res = await recommend_price(source([offer("2000.00")]), Decimal("1000.00"), Decimal("1.00"))
        self.assertEqual((res["price"], res["decision"]), (Decimal("1970.00"), "REVIEW"))


if __name__ == "__main__":
    unittest.main()
