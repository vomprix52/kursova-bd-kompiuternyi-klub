"""Виконує sql/07_queries.sql поблоково і зберігає реальні результати
в docs/results.json (для таблиць у пояснювальній записці).

Перед запуском БД перестворюється (build_db.sh), щоб результати були
відтворюваними. Також перевіряє розмежування доступу за ролями.
"""
import json
import re
import subprocess
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import pymysql

from db import connect

ROOT = Path(__file__).resolve().parent.parent


def fmt(v):
    if v is None:
        return "NULL"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, (date, time)):
        return str(v)
    if isinstance(v, timedelta):
        s = int(v.total_seconds())
        return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"
    if isinstance(v, Decimal):
        return str(v)
    return str(v)


def split_blocks(text):
    blocks, cur = [], None
    for line in text.splitlines():
        m = re.match(r"-- @@ (\w+) \| (.+)", line)
        if m:
            cur = dict(code=m.group(1), title=m.group(2).strip(), lines=[])
            blocks.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    return blocks


def statements(lines):
    """Ділить блок на оператори; позначка '-- expect-error' стосується наступного."""
    out, buf, expect = [], [], False
    for line in lines:
        if line.strip() == "-- expect-error":
            expect = True
            continue
        if line.strip().startswith("--") and not buf:
            continue
        if line.strip().startswith("-- ====="):
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            sql = "\n".join(buf).strip()
            out.append(dict(sql=sql, expect_error=expect))
            buf, expect = [], False
    return out


def run():
    # Демонстрації виконуються із «замороженим» часом (SET TIMESTAMP), а подія
    # ev_booking_housekeeping працює за реальним годинником і позначила б
    # тестові бронювання як неявки. Тому на час прогону планувальник вимкнено.
    adm = connect(database=None)
    adm.cursor().execute("SET GLOBAL event_scheduler = OFF")
    adm.close()
    subprocess.run(["sh", str(ROOT / "build_db.sh")], check=True, capture_output=True)
    text = (ROOT / "sql" / "07_queries.sql").read_text(encoding="utf-8")
    con = connect()
    cur = con.cursor()
    results = {}
    # обсяги тестових даних одразу після завантаження 03_data.sql
    counts = {}
    for t in ["client", "computer", "zone", "tariff", "employee", "shift", "game_session",
              "booking", "balance_transaction", "sale", "sale_item", "product",
              "maintenance_request", "loyalty_level", "pc_config", "position",
              "product_category", "audit_log"]:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cur.fetchone()[0]
    cur.execute("SELECT MIN(started_at), MAX(started_at) FROM game_session")
    counts["period"] = [fmt(v) for v in cur.fetchone()]
    cur.execute("SELECT COUNT(*) FROM sale WHERE sale_type = 'bar'")
    counts["sale_bar"] = cur.fetchone()[0]
    results["COUNTS"] = counts
    for b in split_blocks(text):
        stmts = statements(b["lines"])
        res = dict(code=b["code"], title=b["title"], statements=[])
        for st in stmts:
            item = dict(sql=st["sql"], expect_error=st["expect_error"])
            try:
                cur.execute(st["sql"])
                sets = []
                while True:
                    if cur.description:
                        cols = [d[0] for d in cur.description]
                        rows = [[fmt(v) for v in r] for r in cur.fetchall()]
                        sets.append(dict(columns=cols, rows=rows))
                    if not cur.nextset():
                        break
                item["results"] = sets
                item["rowcount"] = cur.rowcount
                if st["expect_error"]:
                    raise SystemExit(f"{b['code']}: очікувалась помилка, але її немає")
            except pymysql.MySQLError as e:
                if not st["expect_error"]:
                    raise SystemExit(f"{b['code']}: {e}\n{st['sql']}")
                item["error"] = f"ERROR {e.args[0]}: {e.args[1]}"
            res["statements"].append(item)
        results[b["code"]] = res
    cur.execute("SET TIMESTAMP = DEFAULT")
    cur.execute("SET GLOBAL event_scheduler = ON")
    con.close()

    # Перевірка розмежування доступу (матриця ролей)
    checks = [
        ("kc_operator", "Operator#2026", "UPDATE client SET balance = 99999 WHERE client_id = 1"),
        ("kc_operator", "Operator#2026", "SELECT COUNT(*) FROM v_hall_status"),
        ("kc_tech", "Tech#2026", "SELECT COUNT(*) FROM balance_transaction"),
        ("kc_client_app", "Client#2026", "SELECT phone FROM client LIMIT 1"),
        ("kc_owner", "Owner#2026", "DELETE FROM game_session WHERE session_id = 1"),
    ]
    acl = []
    for user, pwd, sql in checks:
        c = connect(user=user, password=pwd)
        k = c.cursor()
        try:
            k.execute(sql)
            out = "OK: " + ", ".join(fmt(v) for v in (k.fetchone() or []))
        except pymysql.MySQLError as e:
            out = f"ERROR {e.args[0]}: {e.args[1]}"
        acl.append(dict(user=user, sql=sql, result=out))
        c.close()
    results["ACL"] = acl

    (ROOT / "docs" / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print("ok", len(results))


if __name__ == "__main__":
    run()
