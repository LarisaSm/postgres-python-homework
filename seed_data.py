from uuid import UUID
from postgres_driver import add_user, add_order


def seed_data(cur):
    users = [
        ("Алиса", 28, "alice@example.com"),
        ("Максим", 35, "maxim@example.com"),
        ("Елена", 24, "elena@example.com"),
    ]

    user_ids = {}

    for name, age, email in users:
        user_ids[email] = add_user(cur, name, age, email)

    orders = [
        (
            "alice@example.com",
            "499.90",
            UUID("11111111-1111-4111-8111-111111111111"),
        ),
        (
            "alice@example.com",
            "1250.00",
            UUID("22222222-2222-4222-8222-222222222222"),
        ),
        (
            "maxim@example.com",
            "750.00",
            UUID("33333333-3333-4333-8333-333333333333"),
        ),
    ]

    for email, amount, order_uid in orders:
        add_order(cur, user_ids[email], amount, order_uid)

    print("Тестовые данные проверены и добавлены при необходимости.")