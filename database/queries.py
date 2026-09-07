from database.connection import get_connection
import json
import hashlib
import hmac
import secrets


PAGE_SIZE = 8


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password, stored_password):
    if not stored_password.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(password, stored_password)
    _, salt, expected = stored_password.split("$", 2)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return hmac.compare_digest(actual, expected)


def create_user(name, email, password):
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hash_password(password)),
            )
            connection.commit()
            return cursor.lastrowid
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()


def get_user_by_email(email):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, email, password FROM users WHERE email = %s LIMIT 1",
            (email,),
        )
        user = cursor.fetchone()
        cursor.close()
    return user


def build_attraction(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "description": row["description"],
        "address": row["address"],
        "transport": row["transport"],
        "mrt": None if row["mrt"] in ("", "None") else row["mrt"],
        "lat": float(row["latitude"]),
        "lng": float(row["longitude"]),
        "images": row["images"].split(",") if row["images"] else [],
    }


def get_attractions(page, keyword=None, category=None):
    conditions = []
    params = []

    if category:
        conditions.append("c.name = %s")
        params.append(category)

    if keyword:
        conditions.append("(a.name LIKE %s OR m.name = %s)")
        params.extend([f"%{keyword}%", keyword])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = page * PAGE_SIZE

    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM attractions AS a
            JOIN categories AS c ON a.category_id = c.id
            JOIN mrt_stations AS m ON a.mrt_id = m.id
            {where_clause}
            """,
            params,
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT
              a.id,
              a.name,
              c.name AS category,
              a.description,
              a.address,
              a.transport,
              m.name AS mrt,
              a.latitude,
              a.longitude,
              GROUP_CONCAT(ai.image_url ORDER BY ai.position SEPARATOR ',') AS images
            FROM attractions AS a
            JOIN categories AS c ON a.category_id = c.id
            JOIN mrt_stations AS m ON a.mrt_id = m.id
            LEFT JOIN attraction_images AS ai ON a.id = ai.attraction_id
            {where_clause}
            GROUP BY
              a.id, a.name, c.name, a.description, a.address, a.transport,
              m.name, a.latitude, a.longitude
            ORDER BY a.id
            LIMIT %s OFFSET %s
            """,
            [*params, PAGE_SIZE, offset],
        )
        rows = cursor.fetchall()
        cursor.close()

    next_page = page + 1 if offset + PAGE_SIZE < total else None
    return {
        "nextPage": next_page,
        "data": [build_attraction(row) for row in rows],
    }


def get_attraction_by_id(attraction_id):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
              a.id,
              a.name,
              c.name AS category,
              a.description,
              a.address,
              a.transport,
              m.name AS mrt,
              a.latitude,
              a.longitude,
              GROUP_CONCAT(ai.image_url ORDER BY ai.position SEPARATOR ',') AS images
            FROM attractions AS a
            JOIN categories AS c ON a.category_id = c.id
            JOIN mrt_stations AS m ON a.mrt_id = m.id
            LEFT JOIN attraction_images AS ai ON a.id = ai.attraction_id
            WHERE a.id = %s
            GROUP BY
              a.id, a.name, c.name, a.description, a.address, a.transport,
              m.name, a.latitude, a.longitude
            """,
            (attraction_id,),
        )
        row = cursor.fetchone()
        cursor.close()

    return build_attraction(row) if row else None


def get_mrts():
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT m.name
            FROM mrt_stations AS m
            JOIN attractions AS a ON a.mrt_id = m.id
            WHERE m.name NOT IN ('', 'None')
            GROUP BY m.id, m.name
            ORDER BY COUNT(a.id) DESC, m.id ASC
            """
        )
        rows = cursor.fetchall()
        cursor.close()

    return [row[0] for row in rows]


def get_categories():
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM categories ORDER BY id")
        rows = cursor.fetchall()
        cursor.close()

    return [row[0] for row in rows]


def get_booking_by_user_id(user_id):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
              b.attraction_id, b.booking_date, b.booking_time, b.price,
              a.name, a.address,
              (SELECT ai.image_url
               FROM attraction_images AS ai
               WHERE ai.attraction_id = a.id
               ORDER BY ai.position
               LIMIT 1) AS image
            FROM bookings AS b
            JOIN attractions AS a ON a.id = b.attraction_id
            WHERE b.user_id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        cursor.close()
    if row is None:
        return None
    return {
        "attraction": {
            "id": row["attraction_id"],
            "name": row["name"],
            "address": row["address"],
            "image": row["image"],
        },
        "date": row["booking_date"].isoformat(),
        "time": row["booking_time"],
        "price": row["price"],
    }


def upsert_booking(user_id, attraction_id, booking_date, booking_time, price):
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO bookings
                  (user_id, attraction_id, booking_date, booking_time, price)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  attraction_id = VALUES(attraction_id),
                  booking_date = VALUES(booking_date),
                  booking_time = VALUES(booking_time),
                  price = VALUES(price)
                """,
                (user_id, attraction_id, booking_date, booking_time, price),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()


def delete_booking_by_user_id(user_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute("DELETE FROM bookings WHERE user_id = %s", (user_id,))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()


def create_unpaid_order(order_number, user_id, price, trip, contact):
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """INSERT INTO orders
                (order_number, user_id, price, status, contact_name, contact_email, contact_phone)
                VALUES (%s, %s, %s, 'UNPAID', %s, %s, %s)""",
                (order_number, user_id, price, contact["name"], contact["email"], contact["phone"]),
            )
            order_id = cursor.lastrowid
            attraction = trip["attraction"]
            cursor.execute(
                """INSERT INTO order_trips
                (order_id, attraction_id, attraction_name, attraction_address, attraction_image, trip_date, trip_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (order_id, attraction["id"], attraction["name"], attraction["address"],
                 attraction["image"], trip["date"], trip["time"]),
            )
            connection.commit()
            return order_id
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()


def save_payment_result(order_id, tappay_result):
    paid = tappay_result.get("status") == 0
    with get_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """INSERT INTO payments
                (order_id, tappay_status, message, rec_trade_id, raw_response)
                VALUES (%s, %s, %s, %s, %s)""",
                (order_id, int(tappay_result.get("status", -1)), str(tappay_result.get("msg", ""))[:500],
                 tappay_result.get("rec_trade_id"), json.dumps(tappay_result, ensure_ascii=False)),
            )
            if paid:
                cursor.execute("UPDATE orders SET status='PAID', paid_at=NOW() WHERE id=%s", (order_id,))
                cursor.execute(
                    "DELETE FROM bookings WHERE user_id=(SELECT user_id FROM orders WHERE id=%s)",
                    (order_id,),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
