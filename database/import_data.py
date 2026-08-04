import argparse
import json
import os
import re
from getpass import getpass
from pathlib import Path

import mysql.connector


DEFAULT_JSON_PATH = Path("data/taipei-attractions.json")
IMAGE_PATH_PATTERN = re.compile(r"/imgs/[^/]+?\.(?:jpg|jpeg|png|gif)", re.IGNORECASE)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import Taipei attraction data from JSON into MySQL."
    )
    parser.add_argument("--json", default=str(DEFAULT_JSON_PATH), help="JSON data path.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", default=int(os.getenv("MYSQL_PORT", "3306")), type=int)
    parser.add_argument(
        "--unix-socket",
        default=os.getenv("MYSQL_UNIX_SOCKET", "/tmp/mysql.sock"),
        help="MySQL Unix socket path. Use an empty string to connect by host/port.",
    )
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "root"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD"))
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE", "taipei_day_trip"))
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not clear existing attraction data before importing.",
    )
    return parser.parse_args()


def read_json(path):
    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    if "list" not in data or not isinstance(data["list"], list):
        raise ValueError("JSON file must contain a list field.")

    return data


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def extract_image_urls(raw_imgurls, img_host):
    host = img_host.rstrip("/")
    paths = IMAGE_PATH_PATTERN.findall(clean_text(raw_imgurls))
    return [f"{host}{path}" for path in paths]


def connect_to_mysql(args):
    password = args.password
    if password is None:
        password = getpass(f"MySQL password for {args.user}: ")

    config = {
        "user": args.user,
        "password": password,
        "database": args.database,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
    }

    if args.unix_socket:
        config["unix_socket"] = args.unix_socket
    else:
        config["host"] = args.host
        config["port"] = args.port

    return mysql.connector.connect(**config)


def reset_tables(cursor):
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE attraction_images")
    cursor.execute("TRUNCATE TABLE attractions")
    cursor.execute("TRUNCATE TABLE categories")
    cursor.execute("TRUNCATE TABLE mrt_stations")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def insert_lookup_values(cursor, table_name, values):
    for value in values:
        cursor.execute(
            f"INSERT INTO {table_name} (name) VALUES (%s) "
            "ON DUPLICATE KEY UPDATE name = VALUES(name)",
            (value,),
        )

    cursor.execute(f"SELECT id, name FROM {table_name}")
    return {name: row_id for row_id, name in cursor.fetchall()}


def import_attractions(connection, data, keep_existing=False):
    attractions = data["list"]
    img_host = clean_text(data.get("img_host"))
    if not img_host:
        raise ValueError("JSON file must contain img_host.")

    cursor = connection.cursor()

    if not keep_existing:
        reset_tables(cursor)

    categories = sorted({clean_text(item.get("CAT")) for item in attractions})
    mrt_stations = sorted({clean_text(item.get("MRT")) for item in attractions})

    category_ids = insert_lookup_values(cursor, "categories", categories)
    mrt_ids = insert_lookup_values(cursor, "mrt_stations", mrt_stations)

    attraction_rows = []
    image_rows = []

    for item in attractions:
        attraction_id = int(item["_id"])
        category = clean_text(item.get("CAT"))
        mrt = clean_text(item.get("MRT"))

        attraction_rows.append(
            (
                attraction_id,
                clean_text(item.get("name")),
                category_ids[category],
                clean_text(item.get("description")),
                clean_text(item.get("address")),
                clean_text(item.get("direction")),
                mrt_ids[mrt],
                clean_text(item.get("latitude")),
                clean_text(item.get("longitude")),
                clean_text(item.get("MEMO_TIME")) or None,
                item.get("rate"),
                clean_text(item.get("SERIAL_NO")) or None,
            )
        )

        for position, image_url in enumerate(
            extract_image_urls(item.get("imgurls"), img_host), start=1
        ):
            image_rows.append((attraction_id, image_url, position))

    cursor.executemany(
        """
        INSERT INTO attractions (
          id, name, category_id, description, address, transport, mrt_id,
          latitude, longitude, memo_time, rate, raw_serial_no
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          name = VALUES(name),
          category_id = VALUES(category_id),
          description = VALUES(description),
          address = VALUES(address),
          transport = VALUES(transport),
          mrt_id = VALUES(mrt_id),
          latitude = VALUES(latitude),
          longitude = VALUES(longitude),
          memo_time = VALUES(memo_time),
          rate = VALUES(rate),
          raw_serial_no = VALUES(raw_serial_no)
        """,
        attraction_rows,
    )

    cursor.executemany(
        """
        INSERT INTO attraction_images (attraction_id, image_url, position)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE image_url = VALUES(image_url)
        """,
        image_rows,
    )

    connection.commit()
    cursor.close()

    return {
        "attractions": len(attraction_rows),
        "categories": len(categories),
        "mrt_stations": len(mrt_stations),
        "images": len(image_rows),
    }


def main():
    args = parse_args()
    data = read_json(args.json)

    connection = connect_to_mysql(args)
    try:
        result = import_attractions(connection, data, keep_existing=args.keep_existing)
    finally:
        connection.close()

    print("Import completed.")
    print(f"Attractions: {result['attractions']}")
    print(f"Categories: {result['categories']}")
    print(f"MRT stations: {result['mrt_stations']}")
    print(f"Images: {result['images']}")


if __name__ == "__main__":
    main()
