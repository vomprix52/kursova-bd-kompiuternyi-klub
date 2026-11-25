"""Готує «живий» стан залу відносно поточного часу, запускає Flask-застосунок
і знімає скриншоти основних екранів через Playwright -> img/ui_*.png."""
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

from db import connect

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "img"
BASE = "http://127.0.0.1:5000"


def live_state():
    subprocess.run(["sh", str(ROOT / "build_db.sh")], check=True, capture_output=True)
    con = connect()
    cur = con.cursor()
    now = datetime.now().replace(second=0, microsecond=0)
    ts = lambda t: cur.execute("SET TIMESTAMP = UNIX_TIMESTAMP(%s)", (t,))
    shift_start = now - timedelta(hours=3, minutes=10)
    ts(shift_start)
    cur.execute("INSERT INTO shift (employee_id, started_at, cash_start) VALUES (4, NOW(), 2000)")
    shift_id = cur.lastrowid
    # власник змінив ціни (тригер аудиту)
    ts(shift_start - timedelta(hours=8))
    cur.execute("SET @app_employee_id = 1")   # ціни змінює керуючий
    cur.execute("UPDATE tariff SET price = 95.00 WHERE tariff_id = 4")
    cur.execute("UPDATE product SET price = 69.00 WHERE product_id = 5")
    cur.execute("UPDATE product SET price = 39.00 WHERE product_id = 1")
    # активні сесії: (клієнт, місце, тариф, хвилин тому, поповнення)
    plan = [(1, 15, 4, 165, 600), (2, 16, 4, 95, 0), (5, 17, 5, 70, 300), (7, 1, 1, 150, 300),
            (9, 3, 2, 120, 200), (11, 4, 1, 45, 200), (12, 7, 1, 30, 0), (14, 10, 1, 20, 150),
            (16, 21, 7, 110, 400), (18, 22, 7, 110, 400), (20, 23, 7, 105, 400),
            (6, 26, 10, 60, 200), (8, 12, 1, 12, 100)]
    for cl, pc, tariff, ago, top in sorted(plan, key=lambda p: -p[3]):
        t = now - timedelta(minutes=ago)
        ts(t - timedelta(minutes=2))
        if top:
            cur.execute("CALL sp_top_up(%s, %s, 'cash', 4, @b)", (cl, top))
        ts(t)
        try:
            cur.execute("CALL sp_start_session(%s, %s, %s, %s, @s)", (cl, pc, tariff, shift_id))
        except Exception:  # замалий баланс — клієнт поповнює і починає знову
            cur.execute("CALL sp_top_up(%s, 300, 'card', 4, @b)", (cl,))
            cur.execute("CALL sp_start_session(%s, %s, %s, %s, @s)", (cl, pc, tariff, shift_id))
    ts(now - timedelta(minutes=5))
    for cl in (19, 27, 10, 4):
        cur.execute("CALL sp_top_up(%s, 300, 'card', 4, @b)", (cl,))
    cur.execute("SET TIMESTAMP = DEFAULT")
    # бронювання, що починається за 10 хв (місце переходить у статус «заброньоване»)
    st = now + timedelta(minutes=10)
    cur.execute("CALL sp_create_booking(4, 6, %s, %s, 4, @bk)", (st, st + timedelta(hours=2)))
    cur.execute("UPDATE computer SET status = 'reserved' WHERE computer_id = 6")
    # завтрашнє бронювання S-02 на 18:00–21:00 – на нього «наткнеться» спроба на скриншоті
    tomorrow = (now + timedelta(days=1)).replace(hour=18, minute=0)
    cur.execute("CALL sp_create_booking(19, 2, %s, %s, 4, @bk2)",
                (tomorrow, tomorrow + timedelta(hours=3)))
    con.close()
    return tomorrow


def shot(page, name, path, full=True):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(IMG / f"ui_{name}.png"), full_page=full)


def login(page, user, pwd, client=False):
    page.goto(BASE + "/logout")
    page.goto(BASE + "/login")
    if client:
        page.click("text=Клієнт")
    page.fill("input[name=login]", user)
    page.fill("input[name=password]", pwd)
    page.click("button.btn")
    page.wait_for_load_state("networkidle")


def main():
    tomorrow = live_state()
    srv = subprocess.Popen([sys.executable, str(ROOT / "app" / "app.py")], cwd=ROOT / "app")
    for _ in range(40):
        try:
            urllib.request.urlopen(BASE + "/login")
            break
        except OSError:
            time.sleep(0.5)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page(viewport={"width": 1400, "height": 860}, device_scale_factor=1.5)
            shot(page, "login", "/login", full=False)
            login(page, "admin3", "admin123")
            # старт сесії через форму
            page.select_option("select[name=client_id] >> nth=0", "19")
            page.select_option("select[name=computer_id]", "18")
            page.select_option("select[name=tariff_id]", "4")
            page.click("form[action='/session/start'] button")
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(IMG / "ui_hall.png"), full_page=True)
            # спроба забронювати місце на зайнятий інтервал -> тригер
            d = tomorrow.strftime("%Y-%m-%d")
            page.goto(BASE + f"/bookings?c=10&pc=2&s={d}T19:00&e={d}T21:00")
            page.click("form button.btn >> text=Забронювати")
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(IMG / "ui_bookings.png"), full_page=True)
            # продаж у барі з балансу клієнта
            page.goto(BASE + "/bar?c=27&m=balance&q5=1&q16=1")
            page.click("text=Пробити чек")
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(IMG / "ui_bar.png"), full_page=True)
            login(page, "owner", "owner123")
            shot(page, "reports", "/reports")
            login(page, "tech1", "tech123")
            shot(page, "tech", "/tech")
            con = connect()
            cur = con.cursor()
            cur.execute("SELECT login FROM client WHERE client_id = 3")
            client_login = cur.fetchone()[0]
            con.close()
            login(page, client_login, "client123", client=True)
            shot(page, "cabinet", "/cabinet")
            b.close()
    finally:
        srv.terminate()
    print("ok")


if __name__ == "__main__":
    main()
