"""Демонстраційний вебінтерфейс «CyberClub» до БД cyberclub.

Уся бізнес-логіка (тарифікація, перевірки, списання) виконується
збереженими процедурами й тригерами MySQL; застосунок лише викликає їх
і показує представлення. Кожна роль працює під власним обліковим записом СКБД,
тому права доступу перевіряє сама СКБД.
"""
import json
from functools import wraps

import pymysql
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = "cyberclub-demo-key"  # лише для локального демо

DB = dict(host="127.0.0.1", port=3307, database="cyberclub", charset="utf8mb4",
          autocommit=True, cursorclass=pymysql.cursors.DictCursor)
# облікові записи СКБД для ролей (див. sql/02_roles.sql)
DB_USERS = {
    "owner": ("kc_owner", "Owner#2026"),
    "operator": ("kc_operator", "Operator#2026"),
    "tech": ("kc_tech", "Tech#2026"),
    "client": ("kc_client_app", "Client#2026"),
}
ROLE_BY_POSITION = {1: "owner", 2: "operator", 3: "tech"}
ROLE_TITLES = {"owner": "Керуючий", "operator": "Адміністратор зали", "tech": "Технік",
               "client": "Клієнт"}
STATUS_UA = {"free": "вільне", "busy": "зайняте", "reserved": "заброньоване",
             "maintenance": "ремонт", "pending": "очікується", "fulfilled": "виконано",
             "cancelled": "скасовано", "no_show": "неявка", "open": "відкрита",
             "in_progress": "в роботі", "resolved": "виконана", "high": "високий",
             "medium": "середній", "low": "низький"}


def db(role=None):
    user, pwd = DB_USERS[role or session["role"]]
    return pymysql.connect(user=user, password=pwd, **DB)


def query(sql, args=None, role=None, one=False):
    con = db(role)
    try:
        with con.cursor() as cur:
            cur.execute(sql, args)
            rows = cur.fetchall()
    finally:
        con.close()
    return (rows[0] if rows else None) if one else rows


def call(sql, args=None, out=None):
    """Виклик процедури; SIGNAL з процедури перетворюється на flash-повідомлення."""
    con = db()
    try:
        with con.cursor() as cur:
            # хто з персоналу виконує дію – тригери запишуть його в журнал аудиту
            if session.get("role") != "client":
                cur.execute("SET @app_employee_id = %s", (session.get("uid"),))
            cur.execute(sql, args)
            while cur.nextset():
                pass
            if out:
                cur.execute(f"SELECT {out} AS v")
                return cur.fetchone()["v"]
        return True
    except pymysql.MySQLError as e:
        flash(e.args[1] if len(e.args) > 1 else str(e), "error")
        return None
    finally:
        con.close()


def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if "role" not in session:
                return redirect(url_for("login"))
            if roles and session["role"] not in roles:
                flash("Недостатньо прав для цього розділу", "error")
                return redirect(url_for("home"))
            return fn(*a, **kw)
        return wrapper
    return deco


@app.context_processor
def inject():
    return dict(ROLE_TITLES=ROLE_TITLES, ua=lambda s: STATUS_UA.get(s, s))


@app.route("/")
def home():
    target = {"owner": "reports", "operator": "hall", "tech": "tech", "client": "cabinet"}
    return redirect(url_for(target.get(session.get("role"), "login")))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_, pwd = request.form["login"].strip(), request.form["password"]
        if request.form.get("kind") == "client":
            u = query("SELECT client_id, login, password_hash, first_name, last_name, status "
                      "FROM client WHERE login = %s", (login_,), role="client", one=True)
            if u and u["status"] == "active" and check_password_hash(u["password_hash"], pwd):
                session.clear()
                session.update(role="client", uid=u["client_id"],
                               name=f'{u["first_name"]} {u["last_name"]}')
                return redirect(url_for("cabinet"))
        else:
            u = query("SELECT employee_id, password_hash, first_name, last_name, position_id "
                      "FROM employee WHERE login = %s AND is_active", (login_,),
                      role="operator", one=True)
            if u and check_password_hash(u["password_hash"], pwd):
                session.clear()
                session.update(role=ROLE_BY_POSITION[u["position_id"]], uid=u["employee_id"],
                               name=f'{u["first_name"]} {u["last_name"]}')
                return redirect(url_for("home"))
        flash("Невірний логін або пароль", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- Адміністратор зали
def current_shift():
    return query("SELECT shift_id, started_at FROM shift WHERE employee_id = %s "
                 "AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
                 (session["uid"],), one=True)


@app.route("/hall")
@login_required("operator")
def hall():
    seats = query("SELECT h.*, c.zone_id FROM v_hall_status h "
                  "JOIN computer c USING (computer_id) ORDER BY h.computer_id")
    zones = query("SELECT zone_id, name FROM zone ORDER BY zone_id")
    tariffs = query("SELECT tariff_id, zone_id, name, tariff_type, price, duration_min "
                    "FROM tariff WHERE is_active ORDER BY zone_id, tariff_id")
    clients = query("SELECT client_id, CONCAT(last_name, ' ', first_name) AS name, balance "
                    "FROM client WHERE status = 'active' ORDER BY last_name")
    stats = dict(busy=sum(s["status"] == "busy" for s in seats), total=len(seats))
    return render_template("hall.html", seats=seats, zones=zones, tariffs=tariffs,
                           clients=clients, shift=current_shift(), stats=stats)


@app.post("/shift/open")
@login_required("operator")
def shift_open():
    if not current_shift():
        call("INSERT INTO shift (employee_id, started_at, cash_start) VALUES (%s, NOW(), %s)",
             (session["uid"], request.form.get("cash", 2000)))
    return redirect(url_for("hall"))


@app.post("/session/start")
@login_required("operator")
def session_start():
    sh = current_shift()
    if not sh:
        flash("Спочатку відкрийте зміну", "error")
        return redirect(url_for("hall"))
    sid = call("CALL sp_start_session(%s, %s, %s, %s, @sid)",
               (request.form["client_id"], request.form["computer_id"],
                request.form["tariff_id"], sh["shift_id"]), out="@sid")
    if sid:
        flash(f"Сесію №{sid} розпочато", "ok")
    return redirect(url_for("hall"))


@app.post("/session/<int:sid>/end")
@login_required("operator")
def session_end(sid):
    if call("CALL sp_end_session(%s)", (sid,)):
        s = query("SELECT minutes_used, cost FROM game_session WHERE session_id = %s",
                  (sid,), one=True)
        flash(f"Сесію №{sid} завершено: {s['minutes_used']} хв, {s['cost']} грн", "ok")
    return redirect(url_for("hall"))


@app.post("/topup")
@login_required("operator")
def topup():
    bal = call("CALL sp_top_up(%s, %s, %s, %s, @bal)",
               (request.form["client_id"], request.form["amount"], request.form["method"],
                session["uid"]), out="@bal")
    if bal is not None:
        flash(f"Баланс поповнено. Новий баланс: {bal} грн", "ok")
    return redirect(request.referrer or url_for("hall"))


# ---------------------------------------------------------------- Бронювання
@app.route("/bookings", methods=["GET", "POST"])
@login_required("operator")
def bookings():
    if request.method == "POST":
        bid = call("CALL sp_create_booking(%s, %s, %s, %s, %s, @bid)",
                   (request.form["client_id"], request.form["computer_id"],
                    request.form["starts_at"], request.form["ends_at"], session["uid"]),
                   out="@bid")
        if bid:
            flash(f"Бронювання №{bid} створено", "ok")
        return redirect(url_for("bookings"))
    rows = query("""SELECT b.booking_id, c.seat_label, z.name AS zone,
                           CONCAT(cl.last_name, ' ', cl.first_name) AS client,
                           b.starts_at, b.ends_at, b.status
                    FROM booking b JOIN computer c USING (computer_id)
                    JOIN zone z ON z.zone_id = c.zone_id
                    JOIN client cl ON cl.client_id = b.client_id
                    WHERE b.ends_at > NOW() - INTERVAL 1 DAY
                    ORDER BY b.starts_at""")
    seats = query("SELECT computer_id, seat_label FROM computer ORDER BY computer_id")
    clients = query("SELECT client_id, CONCAT(last_name, ' ', first_name) AS name "
                    "FROM client WHERE status = 'active' ORDER BY last_name")
    return render_template("bookings.html", rows=rows, seats=seats, clients=clients)


@app.post("/bookings/<int:bid>/cancel")
@login_required("operator")
def booking_cancel(bid):
    call("UPDATE booking SET status = 'cancelled' WHERE booking_id = %s AND status = 'pending'",
         (bid,))
    return redirect(url_for("bookings"))


# ---------------------------------------------------------------- Бар
@app.route("/bar", methods=["GET", "POST"])
@login_required("operator")
def bar():
    if request.method == "POST":
        items = [{"product_id": int(k[4:]), "qty": int(v)}
                 for k, v in request.form.items() if k.startswith("qty_") and v and int(v) > 0]
        sh = current_shift()
        client_id = request.form.get("client_id") or None
        sale_id = call("CALL sp_bar_sale(%s, %s, %s, %s, %s, @sale)",
                       (client_id, session["uid"], sh["shift_id"] if sh else None,
                        request.form["method"], json.dumps(items)), out="@sale")
        if sale_id:
            total = query("SELECT total FROM sale WHERE sale_id = %s", (sale_id,), one=True)
            flash(f"Чек №{sale_id} на суму {total['total']} грн пробито", "ok")
        return redirect(url_for("bar"))
    products = query("""SELECT p.product_id, p.name, p.price, p.stock_qty, c.name AS category
                        FROM product p JOIN product_category c USING (category_id)
                        WHERE p.is_active ORDER BY c.category_id, p.name""")
    top = query("SELECT * FROM v_bar_popularity ORDER BY popularity_rank LIMIT 5")
    clients = query("SELECT client_id, CONCAT(last_name, ' ', first_name) AS name, balance "
                    "FROM client WHERE status = 'active' ORDER BY last_name")
    return render_template("bar.html", products=products, top=top, clients=clients)


# ---------------------------------------------------------------- Звіти власника
@app.route("/reports")
@login_required("owner")
def reports():
    daily = query("""SELECT work_date, SUM(revenue) AS revenue, SUM(sessions) AS sessions
                     FROM v_zone_daily_revenue
                     WHERE work_date >= (SELECT MAX(work_date) FROM v_zone_daily_revenue)
                                        - INTERVAL 13 DAY
                     GROUP BY work_date ORDER BY work_date""")
    zones = query("""SELECT zone_name, SUM(sessions) AS sessions, SUM(hours_played) AS hours,
                            SUM(revenue) AS revenue
                     FROM v_zone_daily_revenue
                     WHERE work_date >= DATE_FORMAT((SELECT MAX(work_date)
                                                    FROM v_zone_daily_revenue), '%Y-%m-01')
                     GROUP BY zone_name ORDER BY revenue DESC""")
    months = query("""SELECT DATE_FORMAT(started_at, '%Y-%m') AS ym, SUM(cost) AS game_rev,
                             COUNT(*) AS sessions
                      FROM game_session WHERE status = 'finished'
                      GROUP BY ym ORDER BY ym""")
    top = query("SELECT * FROM v_client_stats ORDER BY total_spent DESC LIMIT 7")
    audit = query("SELECT a.*, CONCAT(e.last_name, ' ', LEFT(e.first_name, 1), '.') AS who "
                  "FROM audit_log a LEFT JOIN employee e ON e.employee_id = a.employee_id "
                  "WHERE a.table_name IN ('tariff', 'product') ORDER BY a.audit_id DESC LIMIT 6")
    peak = max([float(d["revenue"]) for d in daily] or [1])
    return render_template("reports.html", daily=daily, zones=zones, months=months, top=top,
                           audit=audit, peak=peak)


# ---------------------------------------------------------------- Технік
@app.route("/tech", methods=["GET", "POST"])
@login_required("tech")
def tech():
    if request.method == "POST":
        call("INSERT INTO maintenance_request (computer_id, reported_by, assigned_to, problem, "
             "priority) VALUES (%s, %s, %s, %s, %s)",
             (request.form["computer_id"], session["uid"], session["uid"],
              request.form["problem"], request.form["priority"]))
        return redirect(url_for("tech"))
    reqs = query("SELECT * FROM v_open_requests ORDER BY FIELD(priority, 'high', 'medium', 'low'), "
                 "created_at")
    seats = query("SELECT h.computer_id, h.seat_label, h.zone_name, h.status FROM v_hall_status h "
                  "ORDER BY h.computer_id")
    return render_template("tech.html", reqs=reqs, seats=seats)


@app.post("/tech/<int:rid>/resolve")
@login_required("tech")
def tech_resolve(rid):
    call("UPDATE maintenance_request SET status = 'resolved', resolved_at = NOW(), "
         "assigned_to = %s, resolution = %s WHERE request_id = %s",
         (session["uid"], request.form.get("resolution") or "Виконано", rid))
    flash(f"Заявку №{rid} закрито", "ok")
    return redirect(url_for("tech"))


# ---------------------------------------------------------------- Кабінет клієнта
@app.route("/cabinet", methods=["GET", "POST"])
@login_required("client")
def cabinet():
    if request.method == "POST":
        bid = call("CALL sp_create_booking(%s, %s, %s, %s, NULL, @bid)",
                   (session["uid"], request.form["computer_id"], request.form["starts_at"],
                    request.form["ends_at"]), out="@bid")
        if bid:
            flash(f"Місце заброньовано, номер бронювання {bid}", "ok")
        return redirect(url_for("cabinet"))
    me = query("SELECT * FROM v_client_stats WHERE client_id = %s", (session["uid"],), one=True)
    my_bookings = query("""SELECT b.booking_id, c.seat_label, b.starts_at, b.ends_at, b.status
                           FROM booking b JOIN computer c USING (computer_id)
                           WHERE b.client_id = %s ORDER BY b.starts_at DESC LIMIT 6""",
                        (session["uid"],))
    tariffs = query("""SELECT z.name AS zone, t.name, t.tariff_type, t.price, t.duration_min
                       FROM tariff t JOIN zone z USING (zone_id) WHERE t.is_active
                       ORDER BY z.zone_id, t.tariff_id""")
    seats = query("SELECT computer_id, seat_label, status FROM computer ORDER BY computer_id")
    return render_template("cabinet.html", me=me, my_bookings=my_bookings, tariffs=tariffs,
                           seats=seats)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
