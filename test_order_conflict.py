import unittest
from uuid import uuid4

import psycopg2

from postgres_driver import add_order, add_user, connect_db, create_tables


class OrderConflictTest(unittest.TestCase):
    def setUp(self):
        conn = connect_db()
        self.addCleanup(conn.close)
        self.addCleanup(conn.rollback)
        self.cur = conn.cursor()
        self.addCleanup(self.cur.close)

        self.cur.execute("CREATE TEMP TABLE test_session (id INT);")
        self.cur.execute("SET LOCAL search_path TO pg_temp;")
        create_tables(self.cur)
        self.user_id = add_user(self.cur, "Алиса", 28, "alice@example.com")

    def test_repeat_and_conflict(self):
        order_uid = uuid4()
        order_id = add_order(self.cur, self.user_id, "499.90", order_uid)
        self.assertEqual(
            add_order(self.cur, self.user_id, "499.900", order_uid), order_id
        )
        with self.assertRaisesRegex(ValueError, "Конфликт заказа"):
            add_order(self.cur, self.user_id, "599.90", order_uid)

        self.cur.execute("SELECT COUNT(*) FROM orders;")
        self.assertEqual(self.cur.fetchone()[0], 1)

    def test_invalid_amounts(self):
        for amount in ("bad", "NaN", "Infinity", "100000000.00", "1.005"):
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(ValueError, "Сумма заказа"):
                    add_order(self.cur, self.user_id, amount, uuid4())

        self.cur.execute("SELECT COUNT(*) FROM orders;")
        self.assertEqual(self.cur.fetchone()[0], 0)

    def test_database_rejects_nan(self):
        with self.assertRaises(psycopg2.errors.CheckViolation):
            self.cur.execute(
                "INSERT INTO orders (user_id, amount, order_uid) VALUES (%s, %s, %s);",
                (self.user_id, "NaN", str(uuid4())),
            )

    def test_repeat_user_requires_matching_data(self):
        self.assertEqual(
            add_user(self.cur, "Алиса", 28, "alice@example.com"), self.user_id
        )
        with self.assertRaisesRegex(ValueError, "Конфликт пользователя"):
            add_user(self.cur, "Алиса", 29, "alice@example.com")


if __name__ == "__main__":
    unittest.main()
