import argparse
import psycopg2

from postgres_driver import connect_db, create_tables, get_user_totals
from seed_data import seed_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Добавить демонстрационные данные",
    )
    args = parser.parse_args()

    conn = None

    try:
        conn = connect_db()
        print("Подключение к PostgreSQL успешно!")

        with conn:
            with conn.cursor() as cur:
                create_tables(cur)

                if args.seed:
                    seed_data(cur)

        with conn.cursor() as cur:
            totals = get_user_totals(cur)

            print("\nСумма заказов по пользователям:")
            print("-" * 35)

            for name, total in totals:
                print(f"{name} — {total:.2f}")

    except psycopg2.Error as error:
        print(f"Ошибка PostgreSQL: {error}")

    except (ValueError, RuntimeError) as error:
        print(f"Ошибка данных: {error}")

    finally:
        if conn is not None:
            conn.close()
            print("\nСоединение закрыто.")


if __name__ == "__main__":
    main()