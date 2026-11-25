"""Генерація ER-діаграм (Mermaid -> PNG) безпосередньо зі схеми БД cyberclub.

Фізична модель будується з information_schema, тому діаграма завжди
відповідає реальній структурі бази даних.
"""
import subprocess
from pathlib import Path

from db import connect

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "img"
MMDC = ROOT / "node_modules" / ".bin" / "mmdc.cmd"

UA = {
    "loyalty_level": "Рівень лояльності", "client": "Клієнт", "zone": "Зона",
    "pc_config": "Конфігурація", "computer": "Ігрове місце", "tariff": "Тариф",
    "position": "Посада", "employee": "Працівник", "shift": "Зміна",
    "booking": "Бронювання", "game_session": "Ігрова сесія",
    "product_category": "Категорія товару", "product": "Товар", "sale": "Чек",
    "sale_item": "Позиція чека", "balance_transaction": "Транзакція балансу",
    "maintenance_request": "Заявка на ремонт", "audit_log": "Журнал аудиту",
}

# Дієслова зв'язків для концептуальної моделі: (дочірня, батьківська) -> текст
VERB = {
    ("client", "loyalty_level"): "має рівень",
    ("computer", "zone"): "розміщене в",
    ("computer", "pc_config"): "має конфігурацію",
    ("tariff", "zone"): "діє в",
    ("employee", "position"): "обіймає",
    ("shift", "employee"): "відпрацьовує",
    ("booking", "client"): "створює",
    ("booking", "computer"): "резервує",
    ("booking", "employee"): "оформлює",
    ("game_session", "client"): "грає",
    ("game_session", "computer"): "відбувається на",
    ("game_session", "tariff"): "оплачується за",
    ("game_session", "shift"): "відкрита в",
    ("game_session", "booking"): "реалізує",
    ("product", "product_category"): "належить до",
    ("sale", "client"): "купує",
    ("sale", "employee"): "продає",
    ("sale", "shift"): "пробита в",
    ("sale_item", "sale"): "містить",
    ("sale_item", "product"): "входить у",
    ("balance_transaction", "client"): "змінює баланс",
    ("balance_transaction", "sale"): "списання за чеком",
    ("sale", "game_session"): "оплачує",
    ("audit_log", "employee"): "фіксує зміни",
    ("balance_transaction", "employee"): "проводить",
    ("maintenance_request", "computer"): "стосується",
    ("maintenance_request", "employee"): "подає / виконує",
}


def load_schema():
    con = connect()
    cur = con.cursor()
    cur.execute("""SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY,
                          EXTRA
                   FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='cyberclub'
                     AND TABLE_NAME IN (SELECT TABLE_NAME FROM information_schema.TABLES
                                        WHERE TABLE_SCHEMA='cyberclub'
                                          AND TABLE_TYPE='BASE TABLE')   -- без представлень
                   ORDER BY TABLE_NAME, ORDINAL_POSITION""")
    cols = {}
    for t, c, typ, nul, key, extra in cur.fetchall():
        cols.setdefault(t, []).append((c, typ, nul, key, extra))
    cur.execute("""SELECT k.TABLE_NAME, k.COLUMN_NAME, k.REFERENCED_TABLE_NAME
                   FROM information_schema.KEY_COLUMN_USAGE k
                   WHERE k.TABLE_SCHEMA='cyberclub' AND k.REFERENCED_TABLE_NAME IS NOT NULL""")
    fks = cur.fetchall()
    cur.execute("""SELECT TABLE_NAME, MAX(COLUMN_NAME) FROM information_schema.STATISTICS
                   WHERE TABLE_SCHEMA='cyberclub' AND NON_UNIQUE=0 AND INDEX_NAME<>'PRIMARY'
                   GROUP BY TABLE_NAME, INDEX_NAME HAVING COUNT(*) = 1""")
    uniq = set(cur.fetchall())
    con.close()
    return cols, fks, uniq


def mm_type(t):
    t = t.split(" ")[0]
    if t.startswith("enum"):
        return "enum"
    return t.replace("(", "_").replace(")", "").replace(",", "_")


# Фрагменти фізичної моделі за предметними областями (для читабельності на A4).
# Таблиці зі списку stubs показуються лише первинним ключем – як «точка входу»
# в іншу частину схеми.
FRAGMENTS = {
    "er_phys_equip": (["zone", "pc_config", "computer", "tariff"], []),
    "er_phys_hall": (["loyalty_level", "client", "booking", "game_session"],
                     ["computer", "tariff", "shift", "employee"]),
    "er_phys_money": (["sale", "sale_item", "product", "product_category",
                       "balance_transaction"], ["game_session", "client", "employee", "shift"]),
    "er_phys_staff": (["position", "employee", "shift", "maintenance_request", "audit_log"],
                      ["computer"]),
}


def physical(cols, fks, uniq, tables=None, stubs=()):
    fkcols = {(t, c) for t, c, _ in fks}
    shown = set(tables or cols) | set(stubs)
    out = ["erDiagram"]
    for t, cl in cols.items():
        if t not in shown:
            continue
        out.append(f"  {t} {{")
        for c, typ, nul, key, extra in cl:
            if "STORED GENERATED" in extra or "VIRTUAL GENERATED" in extra:
                continue
            if t in stubs and key != "PRI":
                continue
            marks = []
            if key == "PRI":
                marks.append("PK")
            if (t, c) in fkcols:
                marks.append("FK")
            if (t, c) in uniq and "PK" not in marks:
                marks.append("UK")
            out.append(f"    {mm_type(typ)} {c} {','.join(marks)}".rstrip())
        out.append("  }")
    for t, c, ref in fks:
        if t not in shown or ref not in shown or (t in stubs and ref in stubs):
            continue
        nullable = next(n for cc, _, n, _, _ in cols[t] if cc == c) == "YES"
        if (t, c) in uniq:          # booking_id у game_session — 1:1
            card = "|o--o|"
        else:
            card = "}o--o|" if nullable else "}o--||"
        out.append(f'  {t} {card} {ref} : "{c}"')
    return "\n".join(out)


def conceptual(cols, fks, uniq):
    out = ["erDiagram"] + [f'  {t}["{UA[t]}"]' for t in UA]
    seen = set()
    for t, c, ref in fks:
        key = (t, ref)
        if key in seen:
            continue
        seen.add(key)
        nullable = next(n for cc, _, n, _, _ in cols[t] if cc == c) == "YES"
        if (t, c) in uniq:
            card = "|o--o|"
        else:
            card = "}o--o|" if nullable else "}o--||"
        out.append(f'  {t} {card} {ref} : "{VERB[key]}"')
    return "\n".join(out)


def render(src, name, width=2400, lr=False):
    if lr:   # горизонтальне компонування – менша висота, читабельніше на A4
        src = src.replace("erDiagram", "erDiagram\n  direction LR", 1)
    mmd = IMG / f"{name}.mmd"
    mmd.write_text(src, encoding="utf-8")
    cfg = IMG / "mermaid_cfg.json"
    cfg.write_text('{"theme":"neutral","er":{"fontSize":16,"useMaxWidth":false},'
                   '"themeVariables":{"fontFamily":"Times New Roman"}}', encoding="utf-8")
    subprocess.run([str(MMDC), "-i", str(mmd), "-o", str(IMG / f"{name}.png"),
                    "-c", str(cfg), "-s", "3", "-b", "white"],
                   check=True, shell=True)


if __name__ == "__main__":
    cols, fks, uniq = load_schema()
    render(conceptual(cols, fks, uniq), "er_conceptual")
    render(physical(cols, fks, uniq), "er_physical", 3200)
    for name, (tables, stubs) in FRAGMENTS.items():
        render(physical(cols, fks, uniq, tables, stubs), name, lr=True)
    print("ok")
