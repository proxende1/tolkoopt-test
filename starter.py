"""Учебный фрагмент для тестового задания ТОЛЬКООПТ.

Python 3.10+, только стандартная библиотека. Запуск примера: python starter.py
В функции recommend_price намеренно есть ошибки. Исправьте её по правилам ниже.
sample_fetch_offers имитирует внешний источник: реальные запросы не нужны.

Контракт fetch_offers(): async-функция без аргументов, возвращает словарь
со status (success / partial / error) и offers (список предложений).
Все суммы на входе — положительные Decimal с точностью до копейки.
seller — строка; delivery_days — неотрицательное целое число или None.
Формат входных данных корректен; дополнительных проверок типов не требуется.
fetch_offers может завершиться исключением или долго ожидать ответа.
current_price — текущая цена; min_price — минимально допустимая цена.
timeout_s — положительное число секунд, по умолчанию 2.

ПРАВИЛА В ПОРЯДКЕ ПРИМЕНЕНИЯ
1. Ограничьте ожидание fetch_offers значением timeout_s. При ошибке источника,
   тайм-ауте или status != success верните текущую цену и HOLD.
2. Учитывайте предложения с известной доставкой не более 6 дней.
   Исключайте собственный магазин MYSHOP независимо от регистра букв.
3. Если подходящих предложений нет, верните текущую цену и HOLD,
   даже если текущая цена ниже min_price.
4. Минимальную цену подходящего конкурента уменьшите на 1,5% и округлите
   вниз до копейки. Рекомендация — максимум из этой суммы и min_price.
5. Если рекомендация отличается от текущей цены более чем на 30% в любую
   сторону, верните рекомендацию и REVIEW. Иначе — рекомендацию и APPLY.
   Ровно 30% допускается. REVIEW означает, что автоматическое применение
   запрещено до ручной проверки.

РЕЗУЛЬТАТ
Словарь с полями price (Decimal), decision (APPLY / REVIEW / HOLD),
reason (короткая понятная причина). Сохраните интерфейс recommend_price;
вспомогательные функции допустимы. Пример ниже после исправления должен
вернуть price = Decimal("4728.00"), decision = "APPLY".

ПРОВЕРКА
Добавьте минимум два автоматических теста: обычный расчёт и один сбой
или граничный случай на ваш выбор. Укажите команду запуска тестов.
Достаточно стандартной библиотеки; pytest также допустим.
"""

import asyncio
from decimal import ROUND_FLOOR, Decimal

OWN_SELLER = "myshop"
MAX_DELIVERY_DAYS = 6
DISCOUNT = Decimal("0.985")          # минус 1,5%
MAX_CHANGE = Decimal("0.30")         # порог ручной проверки, 30%
KOPECK = Decimal("0.01")


def _result(price, decision, reason):
    return {"price": price, "decision": decision, "reason": reason}


def _is_suitable(offer):
    """Правило 2: доставка известна и не дольше 6 дней, продавец не MYSHOP."""
    days = offer["delivery_days"]
    if days is None or days > MAX_DELIVERY_DAYS:
        return False
    return offer["seller"].strip().casefold() != OWN_SELLER


async def recommend_price(fetch_offers, current_price, min_price, timeout_s=2.0):
    # 1. Ограничиваем ожидание источника; любой сбой — HOLD.
    try:
        result = await asyncio.wait_for(fetch_offers(), timeout=timeout_s)
    except asyncio.TimeoutError:  # в 3.11+ это тот же TimeoutError
        return _result(current_price, "HOLD", f"Источник не ответил за {timeout_s} с")
    except Exception as exc:  # noqa: BLE001 — любой сбой источника не должен менять цену
        return _result(current_price, "HOLD", f"Ошибка источника: {type(exc).__name__}")

    status = result.get("status")
    if status != "success":
        return _result(current_price, "HOLD", f"Статус источника: {status}")

    # 2. Отбираем подходящие предложения.
    prices = [offer["price"] for offer in result.get("offers", []) if _is_suitable(offer)]

    # 3. Нет подходящих — цену не трогаем, даже если она ниже min_price.
    if not prices:
        return _result(current_price, "HOLD", "Нет подходящих предложений конкурентов")

    # 4. Минимум минус 1,5%, вниз до копейки, но не ниже min_price.
    competitor = min(prices)
    target = (competitor * DISCOUNT).quantize(KOPECK, rounding=ROUND_FLOOR)
    recommended = max(target, min_price)

    # 5. Изменение больше 30% в любую сторону — только ручная проверка.
    if abs(recommended - current_price) > current_price * MAX_CHANGE:
        return _result(
            recommended,
            "REVIEW",
            f"Изменение больше 30% от текущей цены {current_price}",
        )

    if recommended == min_price and target < min_price:
        reason = f"Цена конкурента {competitor} −1,5% ниже минимальной; взята min_price"
    else:
        reason = f"Минимальная цена конкурента {competitor} −1,5%"
    return _result(recommended, "APPLY", reason)


async def sample_fetch_offers():
    return {
        "status": "success",
        "offers": [
            {"seller": "myshop", "price": Decimal("4300.00"), "delivery_days": 2},
            {"seller": "PARTS", "price": Decimal("4800.00"), "delivery_days": 3},
            {"seller": "SLOW", "price": Decimal("4700.00"), "delivery_days": 8},
        ],
    }


if __name__ == "__main__":
    print(asyncio.run(recommend_price(
        sample_fetch_offers,
        current_price=Decimal("4900.00"),
        min_price=Decimal("4500.00"),
    )))
