from database.connection import get_connection


PAGE_SIZE = 12


def build_attraction(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "description": row["description"],
        "address": row["address"],
        "transport": row["transport"],
        "mrt": row["mrt"],
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
            WHERE m.name <> ''
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
