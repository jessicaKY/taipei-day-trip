import os
from contextlib import contextmanager

import mysql.connector


def get_database_config():
    config = {
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "taipei_day_trip"),
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
    }

    unix_socket = os.getenv("MYSQL_UNIX_SOCKET", "/tmp/mysql.sock")
    if unix_socket:
        config["unix_socket"] = unix_socket
    else:
        config["host"] = os.getenv("MYSQL_HOST", "127.0.0.1")
        config["port"] = int(os.getenv("MYSQL_PORT", "3306"))

    return config


@contextmanager
def get_connection():
    connection = mysql.connector.connect(**get_database_config())
    try:
        yield connection
    finally:
        connection.close()
