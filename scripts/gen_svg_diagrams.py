"""Діаграма варіантів використання та схема процесу обслуговування відвідувача.
Малюються вручну у SVG (точний контроль компонування) і растеризуються Playwright."""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "img"
FONT = 'font-family="Times New Roman" font-size="17"'


def text(x, y, lines, anchor="middle", bold=False, size=17):
    w = ' font-weight="bold"' if bold else ""
    dy0 = -(len(lines) - 1) * size * 0.6
    spans = "".join(f'<tspan x="{x}" dy="{dy0 if i == 0 else size * 1.2}">{t}</tspan>'
                    for i, t in enumerate(lines))
    return (f'<text x="{x}" y="{y + size * 0.35}" text-anchor="{anchor}" '
            f'font-family="Times New Roman" font-size="{size}"{w}>{spans}</text>')


def actor(x, y, label):
    lines = label.split("|")
    return (f'<g stroke="#222" stroke-width="2" fill="none">'
            f'<circle cx="{x}" cy="{y - 38}" r="11"/>'
            f'<line x1="{x}" y1="{y - 27}" x2="{x}" y2="{y + 5}"/>'
            f'<line x1="{x - 18}" y1="{y - 15}" x2="{x + 18}" y2="{y - 15}"/>'
            f'<line x1="{x}" y1="{y + 5}" x2="{x - 14}" y2="{y + 28}"/>'
            f'<line x1="{x}" y1="{y + 5}" x2="{x + 14}" y2="{y + 28}"/></g>'
            + text(x, y + 50 + (len(lines) - 1) * 10, lines, bold=True, size=16))


def ellipse(cx, cy, label, rx=118, ry=30):
    return (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#f2f2f2" stroke="#444" '
            f'stroke-width="1.5"/>' + text(cx, cy, label.split("|"), size=16))


def line(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#333" stroke-width="1.3"/>'


def use_case():
    L, R = 370, 640
    uc = {
        "U1": (L, 70, "Переглянути тарифи|та свій баланс"),
        "U2": (L, 145, "Забронювати місце"),
        "U3": (L, 220, "Зареєструвати клієнта"),
        "U4": (L, 295, "Поповнити баланс"),
        "U5": (L, 370, "Почати / завершити|ігрову сесію"),
        "U6": (L, 445, "Продати товари бару"),
        "U7": (L, 520, "Відкрити / закрити зміну"),
        "U8": (L, 595, "Подати / закрити|заявку на ремонт"),
        "U9": (R, 230, "Змінити тарифи|та ціни"),
        "U10": (R, 310, "Переглянути звіти"),
        "U11": (R, 420, "Керувати ролями|та резервними копіями"),
    }
    actors = {"CL": (75, 110, "Клієнт"), "OP": (75, 380, "Адміністратор|зали"),
              "TE": (925, 590, "Технік"), "OW": (925, 270, "Керуючий|клубом"),
              "DBA": (925, 420, "Адміністратор|БД")}
    links = [("CL", "U1"), ("CL", "U2"), ("OP", "U2"), ("OP", "U3"), ("OP", "U4"), ("OP", "U5"),
             ("OP", "U6"), ("OP", "U7"), ("OP", "U8"), ("TE", "U8"), ("OW", "U9"), ("OW", "U10"),
             ("DBA", "U11")]
    body = [f'<rect x="225" y="20" width="560" height="625" rx="6" fill="#fcfcfc" stroke="#777" '
            f'stroke-dasharray="6 4"/>',
            text(505, 8 + 22, ["Система обліку комп'ютерного клубу"], bold=True, size=17)]
    for a, u in links:
        ax, ay, _ = actors[a]
        ux, uy, _ = uc[u]
        sx = ax + 22 if ux > ax else ax - 22
        ex = ux - 118 if ux > ax else ux + 118
        body.append(line(sx, ay - 15, ex, uy))
    body += [ellipse(*v) for v in uc.values()]
    body += [actor(*v) for v in actors.values()]
    return 1000, 670, "".join(body)


def box(cx, cy, label, w=170, h=62, rounded=False):
    r = 28 if rounded else 4
    return (f'<rect x="{cx - w / 2}" y="{cy - h / 2}" width="{w}" height="{h}" rx="{r}" '
            f'fill="#f2f2f2" stroke="#444" stroke-width="1.5"/>' + text(cx, cy, label.split("|")))


def diamond(cx, cy, label, w=190, h=104):
    pts = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
    return (f'<polygon points="{pts}" fill="#e9e9e9" stroke="#444" stroke-width="1.5"/>'
            + text(cx, cy, label.split("|")))


def arrow(points, label=None, lx=None, ly=None):
    d = " ".join(f"{x},{y}" for x, y in points)
    s = (f'<polyline points="{d}" fill="none" stroke="#333" stroke-width="1.6" '
         f'marker-end="url(#arr)"/>')
    if label:
        s += (f'<rect x="{lx - 16}" y="{ly - 11}" width="32" height="20" fill="#fff"/>'
              + text(lx, ly, [label], size=15))
    return s


def process():
    b = [
        box(95, 90, "Відвідувач|прийшов", w=150, rounded=True),
        diamond(320, 90, "Є обліковий|запис?"),
        box(580, 90, "Вибір вільного або|заброньованого|місця і тарифу", w=190, h=78),
        diamond(840, 90, "Коштів|досить?", w=170),
        box(320, 215, "Реєстрація|клієнта"),
        box(840, 215, "Поповнення|балансу"),
        box(840, 345, "Старт сесії;|ПК «зайнятий»"),
        box(580, 345, "Гра, покупки|в барі"),
        diamond(320, 345, "Клієнт завершує|або час вичерпано", w=230, h=110),
        box(95, 345, "Розрахунок|вартості,|списання", w=150, h=78),
        box(95, 470, "Рівень лояльності;|ПК «вільний»", w=190),
    ]
    a = [
        arrow([(170, 90), (223, 90)]),
        arrow([(415, 90), (483, 90)], "так", 449, 78),
        arrow([(320, 142), (320, 182)], "ні", 338, 160),
        arrow([(405, 215), (580, 215), (580, 131)]),
        arrow([(675, 90), (753, 90)]),
        arrow([(822, 132), (822, 182)], "ні", 802, 160),
        arrow([(858, 182), (858, 132)]),
        arrow([(925, 90), (960, 90), (960, 345), (927, 345)], "так", 960, 210),
        arrow([(755, 345), (667, 345)]),
        arrow([(495, 345), (437, 345)]),
        arrow([(205, 345), (172, 345)]),
        arrow([(95, 384), (95, 437)]),
    ]
    defs = ('<defs><marker id="arr" markerWidth="10" markerHeight="8" refX="9" refY="4" '
            'orient="auto"><polygon points="0,0 10,4 0,8" fill="#333"/></marker></defs>')
    return 1000, 510, defs + "".join(a) + "".join(b)


def render(name, spec):
    w, h, body = spec
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'
    (IMG / f"{name}.svg").write_text(svg, encoding="utf-8")
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": w, "height": h}, device_scale_factor=3)
        pg.set_content(f'<html><body style="margin:0;background:#fff">{svg}</body></html>')
        pg.locator("svg").screenshot(path=str(IMG / f"{name}.png"))
        br.close()


if __name__ == "__main__":
    render("use_case", use_case())
    render("process", process())
    print("ok")
