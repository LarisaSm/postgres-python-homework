import os
import psycopg2
from decimal import Context, Decimal, InvalidOperation
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
            amount NUMERIC(10,2) NOT NULL
                CONSTRAINT orders_amount_not_nan CHECK (amount <> 'NaN'::numeric),
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
        "SELECT id, name, age FROM users WHERE email = %s FOR KEY SHARE;",
        (email,),
    )
    existing = cur.fetchone()
    if existing is None:
        raise RuntimeError(
            f"Пользователь с email {email} исчез после конфликта. Повторите операцию."
        )

    existing_id, existing_name, existing_age = existing
    if (existing_name, existing_age) != (name, age):
        raise ValueError(
            f"Конфликт пользователя {email}: имя или возраст отличаются"
        )
    return existing_id


def add_order(cur, user_id, amount, order_uid):
    try:
        amount = Decimal(str(amount))
    except InvalidOperation as error:
        raise ValueError("Сумма заказа должна быть числом") from error

    max_amount = Decimal("99999999.99")
    if not amount.is_finite() or not -max_amount <= amount <= max_amount:
        raise ValueError("Сумма заказа должна быть конечной и в диапазоне ±99999999.99")

    normalized_amount = amount.quantize(Decimal("0.01"), context=Context(prec=10))
    if normalized_amount != amount:
        raise ValueError("Сумма заказа должна быть указана с точностью до копейки")
    amount = normalized_amount
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
