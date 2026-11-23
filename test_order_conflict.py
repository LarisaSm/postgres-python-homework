from postgres_driver import connect_db, add_order

conn = None

try:
    conn = connect_db()

    with conn.cursor() as cur:
        # Находим тестовый заказ по его UUID
        cur.execute(
            """
            SELECT user_id, amount
            FROM orders
            WHERE order_uid = %s;
            """,
            ("11111111-1111-4111-8111-111111111111",),
        )

        order = cur.fetchone()

        if order is None:
            raise RuntimeError(
                "Тестовый заказ не найден. "
                "Сначала выполните python main.py --seed"
            )

        user_id, original_amount = order

        # Пробуем повторно использовать UUID с другой суммой
        try:
            add_order(
                cur,
                user_id=user_id,
                amount=original_amount + 100,
                order_uid="11111111-1111-4111-8111-111111111111",
            )

        except ValueError as error:
            assert "Конфликт заказа" in str(error)
            print("ТЕСТ ПРОЙДЕН: конфликт UUID обнаружен")

        else:
            raise AssertionError(
                "ТЕСТ НЕ ПРОЙДЕН: конфликт UUID не обнаружен"
            )

finally:
    if conn is not None:
        conn.close()
        print("Соединение закрыто.")