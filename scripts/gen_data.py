"""Генератор тестових даних для БД cyberclub -> sql/03_data.sql.

Дані моделюють роботу клубу з 01.07.2026 по 30.09.2026 і узгоджені
з бізнес-правилами: сесії на одному місці та в одного клієнта не
перетинаються, баланс ніколи не стає від'ємним, вартість сесії
обчислюється за тією самою формулою, що й у функції fn_session_cost,
а баланс клієнта дорівнює сумі його транзакцій.
"""
import random
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path

from werkzeug.security import generate_password_hash

random.seed(2026)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sql" / "03_data.sql"

P_START = datetime(2026, 7, 1)
P_END = datetime(2026, 10, 1)
NOW = datetime(2026, 10, 6, 12, 0)


def money(fr):
    """Округлення half-up до копійок (як ROUND() для DECIMAL у MySQL)."""
    return Decimal(fr.numerator) / Decimal(fr.denominator) if False else \
        (Decimal(fr.numerator) / Decimal(fr.denominator)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def hourly_cost(price, minutes, disc):
    # ROUND(price * minutes * (100 - disc) / 6000, 2)
    return money(Fraction(Decimal(price)) * minutes * (100 - Fraction(Decimal(disc))) / 6000)


def package_cost(price, disc):
    return money(Fraction(Decimal(price)) * (100 - Fraction(Decimal(disc))) / 100)


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, Decimal)):
        return str(v)
    if isinstance(v, datetime):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
    if isinstance(v, date):
        return "'" + v.isoformat() + "'"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


# ----------------------------------------------------------------------------
# Довідники
# ----------------------------------------------------------------------------
LEVELS = [(1, "Новачок", "0.00", "0.00"), (2, "Бронза", "1000.00", "3.00"),
          (3, "Срібло", "2500.00", "5.00"), (4, "Золото", "5000.00", "7.00"),
          (5, "Платина", "9000.00", "10.00")]

ZONES = [(1, "STD", "Standard", "Основна зала: 14 ігрових ПК, монітори 165 Гц"),
         (2, "VIP", "VIP", "Окрема зала: 6 ПК з топовою конфігурацією, крісла DXRacer"),
         (3, "BTC", "Bootcamp", "Кімната для команди 5×5 з голосовим зв'язком і проєктором"),
         (4, "CNS", "Console", "Консольна зона: PlayStation 5 та телевізори 55\"")]

CONFIGS = [
    (1, "Standard-2024", "Intel Core i5-13400F", "NVIDIA GeForce RTX 4060 8 ГБ", 16,
     "SSD NVMe 1 ТБ", "AOC 24G2SP 23,8\"", 165),
    (2, "VIP-2025", "AMD Ryzen 7 7800X3D", "NVIDIA GeForce RTX 4070 SUPER 12 ГБ", 32,
     "SSD NVMe 2 ТБ", "ASUS ROG Strix XG27ACS 27\"", 180),
    (3, "Bootcamp-2025", "Intel Core i7-14700F", "NVIDIA GeForce RTX 4070 12 ГБ", 32,
     "SSD NVMe 1 ТБ", "ZOWIE XL2546K 24,5\"", 240),
    (4, "Console-PS5", "Sony PlayStation 5 Slim (AMD Zen 2, 8 ядер)",
     "AMD RDNA 2 (інтегрована)", 16, "SSD 1 ТБ", "LG OLED55C4 55\"", 120),
]

COMPUTERS = []  # (id, seat, zone, config, ip, status, installed)
cid = 0
for zone, prefix, cnt, cfg, ipbase, inst in [(1, "S", 14, 1, 11, date(2024, 8, 20)),
                                             (2, "V", 6, 2, 31, date(2025, 3, 15)),
                                             (3, "B", 5, 3, 41, date(2025, 3, 15)),
                                             (4, "C", 3, 4, 51, date(2025, 9, 1))]:
    for i in range(1, cnt + 1):
        cid += 1
        COMPUTERS.append([cid, f"{prefix}-{i:02d}", zone, cfg, f"192.168.10.{ipbase + i - 1}",
                          "free", inst])
PCS_BY_ZONE = {z: [c[0] for c in COMPUTERS if c[2] == z] for z in range(1, 5)}

# (id, zone, name, type, price, duration, from_h, to_h)
TARIFFS = [
    (1, 1, "Погодинний", "hourly", "60.00", None, None, None),
    (2, 1, "3 години", "package", "160.00", 180, None, None),
    (3, 1, "Нічний", "package", "250.00", 600, 22, 2),
    (4, 2, "Погодинний", "hourly", "90.00", None, None, None),
    (5, 2, "3 години", "package", "240.00", 180, None, None),
    (6, 2, "Нічний", "package", "380.00", 600, 22, 2),
    (7, 3, "Погодинний", "hourly", "80.00", None, None, None),
    (8, 3, "5 годин", "package", "350.00", 300, None, None),
    (9, 4, "Погодинний", "hourly", "100.00", None, None, None),
    (10, 4, "2 години", "package", "180.00", 120, None, None),
]
T = {t[0]: t for t in TARIFFS}

POSITIONS = [(1, "Керуючий клубом", "160.00"), (2, "Адміністратор зали", "95.00"),
             (3, "Технік", "110.00")]

# (id, last, first, phone, login, password, position, hired)
EMPLOYEES = [
    (1, "Мельник", "Олександр", "+380671234501", "owner", "owner123", 1, date(2024, 8, 1)),
    (2, "Ковальчук", "Ірина", "+380671234502", "admin1", "admin123", 2, date(2024, 8, 15)),
    (3, "Савчук", "Дмитро", "+380671234503", "admin2", "admin123", 2, date(2024, 9, 1)),
    (4, "Ткачук", "Марія", "+380671234504", "admin3", "admin123", 2, date(2025, 2, 10)),
    (5, "Поліщук", "Андрій", "+380671234505", "admin4", "admin123", 2, date(2025, 6, 2)),
    (6, "Гнатюк", "Віталій", "+380671234506", "tech1", "tech123", 3, date(2024, 8, 1)),
    (7, "Романюк", "Сергій", "+380671234507", "tech2", "tech123", 3, date(2025, 4, 14)),
]

CATEGORIES = [(1, "Напої"), (2, "Енергетики"), (3, "Снеки"), (4, "Кава та чай"),
              (5, "Гаряча їжа")]
# (id, cat, name, price, popularity)
PRODUCTS = [
    (1, 1, "Coca-Cola 0,5 л", "35.00", 9), (2, 1, "Sprite 0,5 л", "35.00", 4),
    (3, 1, "Моршинська негазована 0,5 л", "22.00", 6), (4, 1, "Fuze Tea лимон 0,5 л", "38.00", 3),
    (5, 2, "Monster Energy 0,5 л", "65.00", 8), (6, 2, "Red Bull 0,25 л", "70.00", 5),
    (7, 2, "Burn 0,5 л", "55.00", 5), (8, 2, "Non Stop 0,5 л", "45.00", 6),
    (9, 3, "Lay's сметана та зелень 120 г", "70.00", 6), (10, 3, "Pringles Original 165 г", "115.00", 3),
    (11, 3, "Snickers 50 г", "35.00", 5), (12, 3, "Сухарики Flint 110 г", "30.00", 4),
    (13, 4, "Американо", "40.00", 5), (14, 4, "Капучино", "55.00", 4), (15, 4, "Чай чорний", "25.00", 2),
    (16, 5, "Хот-дог", "75.00", 5), (17, 5, "Бургер класичний", "110.00", 3),
    (18, 5, "Мівіна курка (з окропом)", "35.00", 4),
]
PRICE = {p[0]: Decimal(p[3]) for p in PRODUCTS}
STOCK = {p[0]: 400 for p in PRODUCTS}

# ----------------------------------------------------------------------------
# Клієнти
# ----------------------------------------------------------------------------
LAST = ["Бондаренко", "Шевчук", "Коваленко", "Кравчук", "Олійник", "Лисенко", "Мороз", "Павлюк",
        "Литвин", "Марчук", "Дячук", "Карпюк", "Остапчук", "Юрчук", "Захарчук", "Хомич",
        "Левчук", "Сидорук", "Кушнір", "Гуменюк", "Дмитрук", "Ярошук", "Борисюк", "Вознюк",
        "Пилипчук", "Степанюк", "Нестерук", "Климчук", "Мартинюк", "Демчук", "Онищук",
        "Тимощук", "Головатюк", "Панасюк", "Семенюк", "Федорчук", "Костюк", "Зінчук",
        "Бабій", "Гордійчук", "Луцюк", "Білик", "Шульга", "Вакулюк", "Сахнюк", "Приходько",
        "Савицький", "Бабенко", "Кондратюк", "Мисюк", "Ничипорук", "Олексюк", "Петрук",
        "Рудь", "Сорока", "Ткач", "Усик", "Фесюк", "Хвищук", "Цимбалюк", "Чорновол", "Шевчишин",
        "Яцюк", "Андрійчук", "Богуш", "Валь", "Грищук", "Дацюк", "Жук", "Іщук", "Каленюк",
        "Лук'янчук", "Мазур", "Назарук", "Осадчук", "Плахотнюк", "Русин", "Сай", "Трохимчук",
        "Фещук"]
MALE = ["Артем", "Максим", "Владислав", "Денис", "Богдан", "Назар", "Ярослав", "Олег", "Тарас",
        "Іван", "Роман", "Микола", "Євген", "Кирило", "Данило", "Остап", "Юрій", "Віктор",
        "Ілля", "Матвій", "Вадим", "Антон", "Михайло", "Павло"]
FEMALE = ["Анна", "Софія", "Вікторія", "Дарина", "Юлія", "Катерина"]
TR = dict(zip("абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'",
              ["a", "b", "v", "h", "g", "d", "e", "ie", "zh", "z", "y", "i", "i", "i", "k", "l", "m",
               "n", "o", "p", "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "iu", "ia", ""]))


def translit(s):
    return "".join(TR.get(ch, ch) for ch in s.lower())


def fem_last(ln):
    if ln.endswith("ький"):
        return ln[:-4] + "ька"
    return ln


CLIENT_PWD = generate_password_hash("client123", method="pbkdf2:sha256", salt_length=12)
clients = []
phones = set()
for i in range(80):
    cid = i + 1
    female = i % 8 == 5
    fn = random.choice(FEMALE) if female else random.choice(MALE)
    ln = fem_last(LAST[i]) if female else LAST[i]
    while True:
        ph = "+380" + random.choice(["67", "68", "96", "97", "98", "50", "66", "95", "63", "73",
                                     "93"]) + f"{random.randint(0, 9999999):07d}"
        if ph not in phones:
            phones.add(ph)
            break
    login = f"{translit(fn)}_{translit(ln)[:4]}{random.randint(1, 99)}"
    email = None
    if random.random() < 0.7:
        email = f"{translit(fn)}.{translit(ln)}{random.randint(1, 999)}@" + random.choice(
            ["gmail.com", "ukr.net", "gmail.com", "i.ua"])
    birth = date(random.randint(1992, 2009), random.randint(1, 12), random.randint(1, 28))
    if cid <= 66:
        reg = datetime(2025, 6, 1) + timedelta(days=random.randint(0, 390),
                                               hours=random.randint(10, 21),
                                               minutes=random.randint(0, 59))
    else:
        reg = datetime(2026, 7, 5) + timedelta(days=random.randint(0, 50),
                                               hours=random.randint(10, 21),
                                               minutes=random.randint(0, 59))
    if cid <= 16:
        weight, pref = 9, random.choice([1, 1, 2, 2, 3])
    elif cid <= 45:
        weight, pref = 3, random.choice([1, 1, 1, 2, 4])
    else:
        weight, pref = 1, random.choice([1, 1, 4, 2])
    clients.append(dict(id=cid, login=login, last=ln, first=fn, phone=ph, email=email, birth=birth,
                        reg=reg, balance=Decimal("0.00"), spent=Decimal("0.00"), level=1,
                        status="active", weight=weight, pref=pref, busy=[]))
CL = {c["id"]: c for c in clients}


def level_for(spent, cur):
    """Рівень лише підвищується (як у тригері trg_client_bu)."""
    reached = max(lid for lid, _, mn, _ in LEVELS if spent >= Decimal(mn))
    return max(cur, reached)


def disc_of(c):
    return Decimal(LEVELS[c["level"] - 1][3])


# ----------------------------------------------------------------------------
# Зміни: денна 09:00–21:00 (адміністратори 2/3), нічна 21:00–09:00 (4/5)
# ----------------------------------------------------------------------------
shifts = []
d = P_START.date() - timedelta(days=1)
while d < P_END.date():
    k = (d - P_START.date()).days
    if d >= P_START.date():
        shifts.append(dict(id=0, emp=2 if k % 2 == 0 else 3,
                           start=datetime.combine(d, datetime.min.time()) + timedelta(hours=9),
                           cash=Decimal("0")))
    shifts.append(dict(id=0, emp=4 if k % 2 == 0 else 5,
                       start=datetime.combine(d, datetime.min.time()) + timedelta(hours=21),
                       cash=Decimal("0")))
    d += timedelta(days=1)
for s in shifts:
    s["end"] = s["start"] + timedelta(hours=12)
shifts = [s for s in shifts if s["end"] > P_START]
shifts.sort(key=lambda s: s["start"])
for i, s in enumerate(shifts, 1):
    s["id"] = i
    s["cash_start"] = Decimal(random.choice([1500, 2000, 2000, 2500]))


def shift_at(t):
    for s in shifts:
        if s["start"] <= t < s["end"]:
            return s
    raise ValueError(t)


# ----------------------------------------------------------------------------
# Заявки на обслуговування (блокують місце, якщо пріоритет високий)
# ----------------------------------------------------------------------------
pc_busy = {c[0]: [] for c in COMPUTERS}
PROBLEMS = [
    ("Не працює гарнітура HyperX Cloud II (лівий канал)", "low", "Замінено гарнітуру з резерву"),
    ("Перегрів GPU, у CS2 падає FPS", "high", "Почищено від пилу, замінено термопасту"),
    ("Не вмикається монітор", "high", "Замінено блок живлення монітора"),
    ("Залипає клавіша W", "medium", "Замінено клавіатуру HyperX Alloy Origins"),
    ("BSOD під час запуску Valorant", "high", "Перевстановлено драйвер NVIDIA 5xx"),
    ("Не працює геймпад DualSense", "medium", "Замінено акумулятор геймпада"),
    ("Сильно шумить кулер процесора", "medium", "Замінено кулер на DeepCool AK400"),
    ("Планова чистка від пилу", "low", "Виконано планове обслуговування"),
    ("Пропадає мережа, втрати пакетів", "high", "Переобтиснуто патч-корд, замінено порт комутатора"),
    ("Миша Logitech G102 робить подвійний клік", "medium", "Замінено мишу"),
    ("Пошкоджено кабель HDMI", "medium", "Замінено кабель HDMI 2.1"),
    ("Не оновлюється клієнт Steam", "low", "Очищено кеш Steam, оновлено клієнт"),
    ("Тріщина на коврику для миші", "low", "Замінено коврик"),
    ("Комп'ютер перезавантажується під навантаженням", "high", "Замінено блок живлення на 750 Вт"),
]
requests = []
for prob, prio, res in PROBLEMS:
    pc = random.choice(COMPUTERS)[0]
    created = P_START + timedelta(days=random.randint(1, 88), hours=random.randint(9, 20),
                                  minutes=random.randint(0, 59))
    resolved = created + timedelta(hours=random.randint(1, 30), minutes=random.randint(0, 59))
    tech = random.choice([6, 7])
    requests.append(dict(pc=pc, rep=shift_at(created)["emp"], tech=tech, prob=prob, prio=prio,
                         status="resolved", created=created, resolved=resolved, res=res))
    if prio == "high":
        pc_busy[pc].append((created, resolved))
# дві відкриті заявки на поточний момент
requests.append(dict(pc=19, rep=3, tech=6, prob="Не запускається, індикатор живлення блимає",
                     prio="high", status="in_progress", created=datetime(2026, 10, 5, 18, 40),
                     resolved=None, res=None))
requests.append(dict(pc=9, rep=4, tech=None, prob="Тьмяніє підсвітка монітора", prio="low",
                     status="open", created=datetime(2026, 10, 6, 10, 15), resolved=None, res=None))
COMPUTERS[18][5] = "maintenance"  # V-05 (id 19) на ремонті


def free(intervals, a, b, gap=timedelta(minutes=5)):
    return all(b + gap <= s or a >= e + gap for s, e in intervals)


# ----------------------------------------------------------------------------
# Моделювання відвідувань
# ----------------------------------------------------------------------------
sessions, txs, sales, bookings = [], [], [], []


def add_tx(c, typ, amount, t, method="none", session=None, sale=None, emp=None):
    c["balance"] += amount
    assert c["balance"] >= 0, (c["id"], typ, amount)
    txs.append(dict(client=c["id"], type=typ, amount=amount, after=c["balance"], method=method,
                    session=session, sale=sale, emp=emp, t=t))


def charge(c, amount, t, typ, session=None, sale=None):
    add_tx(c, typ, -amount, t, session=session, sale=sale)
    c["spent"] += amount
    c["level"] = level_for(c["spent"], c["level"])


def topup_if_needed(c, need, t):
    if c["balance"] >= need:
        return
    raw = need - c["balance"]
    amount = Decimal(int((raw + random.randint(0, 250)) / 50 + 1) * 50)
    if random.random() < 0.12:
        amount = max(amount, Decimal(1000))
    amount = max(amount, Decimal(100))
    sh = shift_at(t)
    method = random.choice(["cash", "cash", "card"])
    add_tx(c, "topup", amount, t, method=method, emp=sh["emp"])
    if method == "cash":
        sh["cash"] += amount
    if amount >= 1000:
        add_tx(c, "bonus", (amount * Decimal("0.05")).quantize(Decimal("0.01")), t, emp=sh["emp"])


def game_sale(c, s, t):
    """Чек за ігрову сесію (оплата з балансу) і відповідне списання."""
    sh = next(x for x in shifts if x["id"] == s["shift"])
    sale = dict(id=None, type="game", session=s, client=c["id"], emp=sh["emp"], shift=sh["id"],
                t=t, method="balance", total=s["cost"], items={})
    sales.append(sale)
    charge(c, s["cost"], t, "session", sale=sale)


def bar_sale(t, client=None, method=None):
    sh = shift_at(t)
    items = {}
    for _ in range(random.choice([1, 1, 1, 2, 2, 3])):
        pid = random.choices([p[0] for p in PRODUCTS], weights=[p[4] for p in PRODUCTS])[0]
        items[pid] = items.get(pid, 0) + random.choice([1, 1, 1, 2])
    total = sum(PRICE[p] * q_ for p, q_ in items.items())
    if method is None:
        method = random.choice(["cash", "cash", "card"])
    if method == "balance" and (client is None or client["balance"] < total):
        method = "cash"
    for p, q_ in items.items():
        STOCK[p] -= q_
    sale = dict(id=None, type="bar", session=None, client=client["id"] if client else None,
                emp=sh["emp"], shift=sh["id"], t=t, method=method, total=total, items=items)
    sales.append(sale)
    if method == "cash":
        sh["cash"] += total
    if method == "balance":
        charge(client, total, t, "bar", sale=sale)
    return sale


def pick_tariff(zone, start):
    opts = [t for t in TARIFFS if t[1] == zone]
    night = [t for t in opts if t[6] is not None and (start.hour >= 22 or start.hour < 2)]
    if night and random.random() < 0.55:
        return night[0]
    pk = [t for t in opts if t[3] == "package" and t[6] is None]
    if pk and random.random() < 0.22:
        return pk[0]
    return next(t for t in opts if t[3] == "hourly")


def make_session(c, zone, start, tariff=None, want=None, pcs=None):
    tariff = tariff or pick_tariff(zone, start)
    tid, _, _, typ, price, dur, _, _ = tariff
    disc = disc_of(c)
    if typ == "hourly":
        want = want or random.choice([60, 90, 120, 120, 150, 180, 240, 45, 75, 300])
        est = hourly_cost(price, want, disc)
        need = est if random.random() < 0.85 else hourly_cost(price, int(want * 0.6), disc)
        need = max(need, hourly_cost(price, 30, disc))
    else:
        want = want or (random.randint(dur - 150, dur) if dur >= 300 else random.randint(dur - 30, dur))
        need = package_cost(price, disc)
    # пошук вільного місця
    end_guess = start + timedelta(minutes=max(want, dur or 0))
    if not free(c["busy"], start - timedelta(minutes=10), end_guess):
        return None
    cand = [p for p in (pcs or PCS_BY_ZONE[zone]) if free(pc_busy[p], start, end_guess)]
    if not cand:
        return None
    pc = random.choice(cand)
    topup_if_needed(c, need, start - timedelta(minutes=random.randint(1, 4)))
    sh = shift_at(start)
    s = dict(id=None, client=c["id"], pc=pc, tariff=tid, shift=sh["id"], booking=None, start=start,
             disc=disc)
    if typ == "hourly":
        rate_min = Fraction(Decimal(price)) * (100 - Fraction(Decimal(disc))) / 6000
        avail = int(Fraction(c["balance"]) / rate_min)
        avail = min(avail, 720)
        s["planned"] = start + timedelta(minutes=avail)
        minutes = min(want, avail)
        s["end"] = start + timedelta(minutes=minutes)
        s["minutes"] = minutes
        s["cost"] = hourly_cost(price, minutes, disc)
    else:
        s["planned"] = start + timedelta(minutes=dur)
        s["cost"] = package_cost(price, disc)
        game_sale(c, s, start)
        minutes = min(want, dur)
        s["end"] = start + timedelta(minutes=minutes)
        s["minutes"] = minutes
    # покупки в барі під час сесії
    if random.random() < 0.22:
        t = start + timedelta(minutes=random.randint(5, max(6, minutes - 5)))
        method = "balance" if (typ == "package" and random.random() < 0.6) else None
        bar_sale(t, c, method)
    if typ == "hourly":
        game_sale(c, s, s["end"])
    pc_busy[pc].append((start, s["end"]))
    c["busy"].append((start, s["end"]))
    sessions.append(s)
    return s


day = P_START
while day < P_END:
    weekend = day.weekday() >= 4
    visits = []
    for _ in range(random.randint(14, 20) if weekend else random.randint(8, 13)):
        pool = [c for c in clients if c["reg"] < day]
        c = random.choices(pool, weights=[x["weight"] for x in pool])[0]
        hour = random.choices(list(range(10, 24)) + [0, 1],
                              weights=[1, 1, 2, 2, 3, 3, 4, 5, 6, 6, 5, 4, 4, 3, 1, 1])[0]
        start = day + timedelta(hours=hour, minutes=random.randint(0, 59))
        if hour < 2:
            start += timedelta(days=1)
        if start >= P_END:
            continue
        zone = c["pref"] if random.random() < 0.8 else random.choice([1, 1, 2, 4])
        visits.append((start, c, zone, None, None, None))
    # командне тренування в Bootcamp (п'ятниця або неділя)
    if day.weekday() in (4, 6) and random.random() < 0.5:
        start = day + timedelta(hours=random.choice([12, 14, 16]))
        team = random.sample([c for c in clients[:45] if c["reg"] < day], 5)
        for c, pc in zip(team, PCS_BY_ZONE[3]):
            visits.append((start, c, 3, T[8], random.randint(240, 300), [pc]))
    # візити обробляються в хронологічному порядку, щоб баланс кожного
    # клієнта змінювався послідовно
    for start, c, zone, tariff, want, pcs in sorted(visits, key=lambda v: (v[0], v[1]["id"])):
        make_session(c, zone, start, tariff=tariff, want=want, pcs=pcs)
    # анонімні покупки в барі
    if random.random() < 0.35:
        bar_sale(day + timedelta(hours=random.randint(10, 22), minutes=random.randint(0, 59)))
    day += timedelta(days=1)

CL[71]["status"] = "blocked"  # заблокований після порушення правил клубу

# ----------------------------------------------------------------------------
# Бронювання: виконані (прив'язані до сесій), скасовані, неявки, майбутні
# ----------------------------------------------------------------------------
for s in random.sample(sessions, 70):
    if s["booking"] is not None:
        continue
    b_start = s["start"] - timedelta(minutes=random.randint(0, 10))
    span = max(60, (s["minutes"] // 30 + 1) * 30)
    b = dict(id=None, client=s["client"], pc=s["pc"], start=b_start,
             end=b_start + timedelta(minutes=min(span, 720)), status="fulfilled",
             created=b_start - timedelta(hours=random.randint(2, 50)),
             by=None if random.random() < 0.4 else shift_at(b_start - timedelta(hours=1))["emp"],
             session=s)
    if b["created"] < CL[s["client"]]["reg"]:
        continue
    s["booking"] = b
    bookings.append(b)
tries = 0
while sum(1 for b in bookings if b["status"] in ("cancelled", "no_show")) < 18 and tries < 500:
    tries += 1
    c = random.choice([c for c in clients if c["reg"] < P_START])
    pc = random.choice(PCS_BY_ZONE[random.choice([1, 2, 2, 3])])
    st = P_START + timedelta(days=random.randint(1, 88), hours=random.randint(12, 21))
    en = st + timedelta(minutes=random.choice([60, 120, 180]))
    if not free(pc_busy[pc], st, en) or not free(c["busy"], st, en):
        continue
    status = random.choice(["cancelled", "cancelled", "no_show"])
    created = st - timedelta(hours=random.randint(3, 40))
    bookings.append(dict(id=None, client=c["id"], pc=pc, start=st, end=en, status=status,
                         created=created, by=None if random.random() < 0.5 else shift_at(created)["emp"],
                         session=None))
    if status == "no_show":
        pc_busy[pc].append((st, st + timedelta(minutes=15)))
# майбутні (очікувані) бронювання на 7–10 жовтня
future = [(3, 2, "2026-10-07 18:00", 180), (5, 21, "2026-10-07 19:00", 120),
          (1, 1, "2026-10-08 16:00", 120), (8, 15, "2026-10-08 20:00", 240),
          (2, 22, "2026-10-09 18:00", 300), (12, 23, "2026-10-09 18:00", 300),
          (14, 26, "2026-10-09 15:00", 120), (6, 4, "2026-10-10 14:00", 180)]
for cl, pc, st, mins in future:
    st = datetime.fromisoformat(st)
    bookings.append(dict(id=None, client=cl, pc=pc, start=st, end=st + timedelta(minutes=mins),
                         status="pending", created=datetime(2026, 10, 5, 12, 0) + timedelta(
                             minutes=random.randint(0, 1400)), by=None, session=None))

# ----------------------------------------------------------------------------
# Нумерація в хронологічному порядку
# ----------------------------------------------------------------------------
for i, b in enumerate(sorted(bookings, key=lambda b: (b["created"], b["pc"])), 1):
    b["id"] = i
for i, s in enumerate(sorted(sessions, key=lambda s: (s["start"], s["pc"])), 1):
    s["id"] = i
for i, s in enumerate(sorted(sales, key=lambda s: (s["t"], s["type"] != "game")), 1):
    s["id"] = i
txs.sort(key=lambda x: (x["t"], x["client"]))

# касовий підсумок змін
for sh in shifts:
    sh["cash_end"] = sh["cash_start"] + sh["cash"]

# перевірки узгодженості
for c in clients:
    tot = sum(x["amount"] for x in txs if x["client"] == c["id"])
    assert tot == c["balance"], c["id"]
for pc, iv in pc_busy.items():
    iv = sorted(iv)
    for (a1, b1), (a2, b2) in zip(iv, iv[1:]):
        assert b1 <= a2, (pc, a1, a2)

# ----------------------------------------------------------------------------
# Вивід SQL
# ----------------------------------------------------------------------------
lines = ["-- =====================================================================",
         "-- Скрипт 03. Тестові дані (згенеровано scripts/gen_data.py, seed 2026)",
         "-- Період моделювання: 01.07.2026 – 30.09.2026",
         "-- Тестові паролі: клієнти — client123; owner — owner123;",
         "--                 admin1..admin4 — admin123; tech1, tech2 — tech123",
         "-- =====================================================================",
         "USE cyberclub;", "SET NAMES utf8mb4;", ""]


def insert(table, cols, rows, chunk=60):
    for i in range(0, len(rows), chunk):
        part = rows[i:i + chunk]
        lines.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES")
        lines.append(",\n".join("  (" + ", ".join(q(v) for v in r) + ")" for r in part) + ";")
    lines.append("")


insert("loyalty_level", ["level_id", "name", "min_spent", "discount_pct"], LEVELS)
insert("zone", ["zone_id", "code", "name", "description"], ZONES)
insert("pc_config", ["config_id", "name", "cpu", "gpu", "ram_gb", "storage", "monitor", "refresh_hz"],
       CONFIGS)
insert("computer", ["computer_id", "seat_label", "zone_id", "config_id", "ip_address", "status",
                    "installed_at"], COMPUTERS)
insert("tariff", ["tariff_id", "zone_id", "name", "tariff_type", "price", "duration_min",
                  "start_from_h", "start_to_h"], TARIFFS)
insert("position", ["position_id", "title", "hourly_rate"], POSITIONS)
pw_cache = {}
emp_rows = []
for e in EMPLOYEES:
    if e[5] not in pw_cache:
        pw_cache[e[5]] = generate_password_hash(e[5], method="pbkdf2:sha256", salt_length=12)
    emp_rows.append((e[0], e[1], e[2], e[3], e[4], pw_cache[e[5]], e[6], e[7]))
insert("employee", ["employee_id", "last_name", "first_name", "phone", "login", "password_hash",
                    "position_id", "hired_at"], emp_rows)
insert("client", ["client_id", "login", "password_hash", "last_name", "first_name", "phone", "email",
                  "birth_date", "balance", "total_spent", "level_id", "status", "registered_at"],
       [(c["id"], c["login"], CLIENT_PWD, c["last"], c["first"], c["phone"], c["email"], c["birth"],
         c["balance"], c["spent"], c["level"], c["status"], c["reg"]) for c in clients])
insert("shift", ["shift_id", "employee_id", "started_at", "ended_at", "cash_start", "cash_end"],
       [(s["id"], s["emp"], s["start"], s["end"], s["cash_start"], s["cash_end"]) for s in shifts])
insert("booking", ["booking_id", "client_id", "computer_id", "starts_at", "ends_at", "status",
                   "created_at", "created_by"],
       [(b["id"], b["client"], b["pc"], b["start"], b["end"], b["status"], b["created"], b["by"])
        for b in sorted(bookings, key=lambda b: b["id"])])
insert("game_session", ["session_id", "client_id", "computer_id", "tariff_id", "shift_id",
                        "booking_id", "started_at", "planned_end", "ended_at", "minutes_used",
                        "discount_pct", "cost", "status"],
       [(s["id"], s["client"], s["pc"], s["tariff"], s["shift"],
         s["booking"]["id"] if s["booking"] else None, s["start"], s["planned"], s["end"],
         s["minutes"], s["disc"], s["cost"], "finished")
        for s in sorted(sessions, key=lambda s: s["id"])])
insert("product_category", ["category_id", "name"], CATEGORIES)
insert("product", ["product_id", "category_id", "name", "price", "stock_qty"],
       [(p[0], p[1], p[2], p[3], STOCK[p[0]]) for p in PRODUCTS])
insert("sale", ["sale_id", "sale_type", "session_id", "client_id", "employee_id", "shift_id",
                "created_at", "payment_method", "total"],
       [(s["id"], s["type"], s["session"]["id"] if s["session"] else None, s["client"], s["emp"],
         s["shift"], s["t"], s["method"], s["total"])
        for s in sorted(sales, key=lambda s: s["id"])])
insert("sale_item", ["sale_id", "product_id", "quantity", "unit_price"],
       [(s["id"], p, qty, PRICE[p]) for s in sorted(sales, key=lambda s: s["id"])
        for p, qty in sorted(s["items"].items())])
insert("balance_transaction", ["tx_id", "client_id", "tx_type", "amount", "balance_after",
                               "payment_method", "sale_id", "employee_id", "created_at"],
       [(i, x["client"], x["type"], x["amount"], x["after"], x["method"],
         x["sale"]["id"] if x["sale"] else None,
         x["emp"], x["t"]) for i, x in enumerate(txs, 1)])
insert("maintenance_request", ["request_id", "computer_id", "reported_by", "assigned_to", "problem",
                               "priority", "status", "created_at", "resolved_at", "resolution"],
       [(i, r["pc"], r["rep"], r["tech"], r["prob"], r["prio"], r["status"], r["created"],
         r["resolved"], r["res"])
        for i, r in enumerate(sorted(requests, key=lambda r: r["created"]), 1)])

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"clients={len(clients)} pcs={len(COMPUTERS)} sessions={len(sessions)} tx={len(txs)} "
      f"sales={len(sales)} items={sum(len(s['items']) for s in sales)} bookings={len(bookings)} "
      f"shifts={len(shifts)} requests={len(requests)}")
print("levels:", {l: sum(1 for c in clients if c['level'] == l) for l in range(1, 6)})
