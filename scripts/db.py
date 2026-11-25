"""Спільні параметри підключення до локального екземпляра MySQL."""
import pymysql

CONN = dict(host="127.0.0.1", port=3307, user="root", password="",
            database="cyberclub", charset="utf8mb4", autocommit=True)


def connect(**over):
    return pymysql.connect(**{**CONN, **over})
