import os
import psycopg2
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()


def connect_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def create_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            age INT CHECK (age >= 0),
            email TEXT NOT NULL UNIQUE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL
                REFERENCES users(id) ON DELETE CASCADE,
            amount NUMERIC(10,2) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            order_uid UUID NOT NULL UNIQUE
        );
    """)


def add_user(cur, name, age, email):
    cur.execute(
        """
        INSERT INTO users (name, age, email)
        VALUES (%s, %s, %s)
        ON CONFLICT (email) DO NOTHING
        RETURNING id;
        """,
        (name, age, email),
    )

    result = cur.fetchone()

    if result:
        return result[0]

    cur.execute(
        "SELECT id FROM users WHERE email = %s;",
        (email,),
    )
    return cur.fetchone()[0]


def add_order(cur, user_id, amount, order_uid):
    amount = Decimal(str(amount))
    order_uid = str(order_uid)

    # Пытаемся добавить заказ
    cur.execute(
        """
        INSERT INTO orders (user_id, amount, order_uid)
        VALUES (%s, %s, %s)
        ON CONFLICT (order_uid) DO NOTHING
        RETURNING id;
        """,
        (user_id, amount, order_uid),
    )

    result = cur.fetchone()

    if result:
        print(f"Создан новый заказ ID: {result[0]}")
        return result[0]

    # Заказ с таким UUID уже существует
    cur.execute(
        """
        SELECT id, user_id, amount
        FROM orders
        WHERE order_uid = %s;
        """,
        (order_uid,),
    )

    existing = cur.fetchone()

    if existing is None:
        raise RuntimeError(
            "Не удалось получить заказ после конфликта UUID"
        )

    existing_id, existing_user_id, existing_amount = existing

    # Проверяем, совпадают ли данные
    if existing_user_id != user_id or existing_amount != amount:
        raise ValueError(
            f"Конфликт заказа {order_uid}: "
            "UUID существует, но пользователь или сумма отличаются"
        )

    print(f"Заказ ID {existing_id} уже существует, пропускаем.")
    return existing_id


def get_user_totals(cur):
    cur.execute("""
        SELECT u.name,
               COALESCE(SUM(o.amount), 0) AS total_amount
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.id
        GROUP BY u.id, u.name
        ORDER BY total_amount DESC, u.id;
    """)

    return cur.fetchall()