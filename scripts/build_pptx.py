"""Презентація до захисту на фірмовому шаблоні коледжу (python-pptx).

Шаблон береться з презентації минулого року: використовуються лише його
макети (фіолетовий фон, логотип у футері) і декоративні зображення;
усі слайди-приклади видаляються.
"""
import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
PRES = ROOT / "presentation"
TMP = PRES / "tmp"
ASSETS = PRES / "assets"  # декоративні зображення з шаблону коледжу
IMG = ROOT / "img"
TEMPLATE = TMP / "ref_b.pptx"
OUT = PRES / "Prezentatsiia_Hlodovskyi.pptx"
RES = json.loads((ROOT / "docs" / "results.json").read_text(encoding="utf-8"))

WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x1F, 0x12, 0x4D)       # темно-фіолетовий текст на білих картках
PURPLE = RGBColor(0x60, 0x0C, 0xEB)    # фон шаблону
LILAC = RGBColor(0xD9, 0xCC, 0xFF)     # приглушений текст на фіолетовому
FONT = "Arial"


def drop_all_slides(prs):
    lst = prs.slides._sldIdLst
    for sid in list(lst):
        prs.part.drop_rel(sid.rId)
        lst.remove(sid)


def text(slide, x, y, w, h, runs, size=16, color=WHITE, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, name=None, space=6):
    """runs: рядок або список абзаців; абзац – рядок або список (текст, bold)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        parts = para if isinstance(para, list) else [(para, bold)]
        for t, b in parts:
            r = p.add_run()
            r.text = t
            f = r.font
            f.name, f.size, f.bold = FONT, Pt(size), b
            f.color.rgb = color
    return tb


def card(slide, x, y, w, h, fill=WHITE, name=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.adjustments[0] = 0.08
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.fill.background()
    sh.shadow.inherit = False
    if name:
        sh.name = name
    return sh


def circle_num(slide, x, y, d, label, fill=WHITE, color=PURPLE, size=16):
    sh = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.fill.background()
    tf = sh.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.name, r.font.size, r.font.bold = FONT, Pt(size), True
    r.font.color.rgb = color
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return sh


def picture_framed(slide, path, x, y, w=None, h=None, pad=0.06):
    """Зображення на білій картці; задається ширина або висота рамки."""
    iw, ih = Image.open(path).size
    if w is not None:
        pw = w - 2 * pad
        ph = pw * ih / iw
    else:
        ph = h - 2 * pad
        pw = ph * iw / ih
    card(slide, x, y, pw + 2 * pad, ph + 2 * pad)
    slide.shapes.add_picture(str(path), Inches(x + pad), Inches(y + pad), Inches(pw), Inches(ph))
    return pw + 2 * pad, ph + 2 * pad


def corners(slide):
    """Декоративні діагональні лінії шаблону (як у прикладах коледжу)."""
    for name, x, y, rot in (("corner_tl", -1.11, -0.47, 313.29), ("corner_tr", 7.91, -0.47, 41.08)):
        pic = slide.shapes.add_picture(str(ASSETS / f"{name}.png"), Inches(x), Inches(y),
                                       Inches(3.28), Inches(1.67))
        pic.rotation = rot


def title(slide, t):
    text(slide, 1.2, 0.28, 7.6, 0.6, t, size=26, bold=True, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE, name="Заголовок")


def content_slide(prs, t, notes):
    s = prs.slides.add_slide(prs.slide_layouts[1])   # «11_PPTMON slide»: фон + логотип
    corners(s)
    title(s, t)
    s.notes_slide.notes_text_frame.text = notes
    return s


def build():
    prs = Presentation(str(TEMPLATE))
    drop_all_slides(prs)
    L_TITLE = prs.slide_layouts[0]

    # 1 ---------------------------------------------------------------- титул
    s = prs.slides.add_slide(L_TITLE)
    s.shapes.add_picture(str(ASSETS / "pillars.png"), Inches(5.24), Inches(-0.2), Inches(4.65), Inches(6.22))
    s.shapes.add_picture(str(ASSETS / "logo.png"), Inches(0.39), Inches(0.45), Inches(1.66), Inches(0.4))
    text(s, 0.39, 1.1, 5.0, 1.2, ["Курсова робота", "з баз даних"], size=32,
         bold=True, space=0)
    text(s, 0.39, 2.5, 4.7, 1.0,
         "Тема: «Проєктування та реалізація бази даних для автоматизації діяльності "
         "комп'ютерного клубу»", size=15, bold=True)
    text(s, 0.39, 3.85, 4.6, 1.2,
         [[("Глодовський Богдан Михайлович", True)], "ІПЗ-3/2",
          "Керівник: Лагоднюк Д. О.", "Рівне 2026"], size=12, space=1)
    s.notes_slide.notes_text_frame.text = (
        "Шановна комісіє! Тема моєї курсової роботи – проєктування та реалізація бази даних "
        "для автоматизації діяльності комп'ютерного клубу.")

    # 2 ---------------------------------------------------------- проблема/рішення
    s = content_slide(prs, "Проблематика та рішення",
                      "Комп'ютерні клуби – це вже бізнес з кількома зонами, баром, бронюваннями і "
                      "змінами. Облік у зошиті чи таблиці дає помилки в розрахунках, а готові "
                      "системи (Gizmo, SENET, ggLeap) беруть плату за кожне місце і мають закриту "
                      "структуру даних. Моє рішення – власна реляційна БД у MySQL, де правила "
                      "клубу перевіряє сама СКБД.")
    for i, (head, body) in enumerate([
        ("Проблема", ["Сотні операцій за день: сесії, поповнення, бар, бронювання",
                      "Облік у зошиті чи Excel – помилки у вартості часу",
                      "Готові системи: плата за кожне місце, закрита структура даних"]),
        ("Рішення", ["Власна реляційна база даних у MySQL",
                     "Бізнес-правила – тригерами, процедурами, CHECK",
                     "Ролі персоналу і звіти для власника"])]):
        x = 0.55 + i * 4.6
        card(s, x, 1.25, 4.3, 3.1)
        circle_num(s, x + 0.25, 1.4, 0.55, "!" if i == 0 else "✓", fill=PURPLE, color=WHITE, size=18)
        text(s, x + 0.95, 1.43, 3.1, 0.5, head, size=20, bold=True, color=INK,
             anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 0.3, 2.2, 3.8, 2.1, [[("•  " + b, False)] for b in body], size=15,
             color=INK, space=10)
    text(s, 4.43, 2.55, 0.5, 0.5, "→", size=28, bold=True, align=PP_ALIGN.CENTER)

    # 3 ------------------------------------------------------------- мета і етапи
    s = content_slide(prs, "Мета та завдання",
                      "Мета – спроєктувати і реалізувати в MySQL базу даних для автоматизації "
                      "основних процесів клубу та перевірити її на реалістичних даних і "
                      "демонстраційному вебінтерфейсі. Робота пройшла чотири етапи: аналіз, "
                      "проєктування, реалізація в СКБД і інтерфейс.")
    text(s, 0.6, 1.1, 8.8, 0.8,
         "Мета: спроєктувати та реалізувати в MySQL реляційну базу даних для автоматизації "
         "основних процесів комп'ютерного клубу і перевірити її на тестових даних",
         size=15, color=WHITE, align=PP_ALIGN.CENTER)
    steps = [("Аналіз", "процеси клубу, 5 систем-аналогів, вимоги і ролі"),
             ("Проєктування", "18 сутностей, ER-модель, нормалізація до 3НФ"),
             ("Реалізація", "DDL, тестові дані, запити, процедури, тригери"),
             ("Інтерфейс", "Flask-застосунок під ролями СКБД")]
    for i, (h, b) in enumerate(steps):
        x = 0.45 + i * 2.32
        card(s, x, 2.25, 2.12, 2.45)
        circle_num(s, x + 0.76, 2.42, 0.6, str(i + 1), fill=PURPLE, color=WHITE, size=18)
        text(s, x + 0.1, 3.12, 1.92, 0.45, h, size=15, bold=True, color=INK, align=PP_ALIGN.CENTER)
        text(s, x + 0.12, 3.58, 1.88, 1.05, b, size=12, color=INK, align=PP_ALIGN.CENTER)

    # 4 ---------------------------------------------------------- предметна область
    s = content_slide(prs, "Предметна область",
                      "Розглядав клуб на 28 місць у чотирьох зонах. Виділив дев'ять процесів і "
                      "п'ять ролей; на діаграмі – хто що робить у системі. Клієнт не має облікового "
                      "запису в СКБД і працює через застосунок з обмеженою роллю.")
    picture_framed(s, IMG / "use_case.png", 0.4, 1.05, w=5.3)
    facts = [("28", "ігрових місць у 4 зонах: Standard, VIP, Bootcamp, Console"),
             ("9", "процесів: сесії, баланс, бронювання, бар, зміни, ремонт, звіти…"),
             ("5", "ролей: керуючий, адміністратор зали, технік, клієнт, адмін БД")]
    for i, (n, d) in enumerate(facts):
        y = 1.1 + i * 1.18
        text(s, 5.95, y, 1.1, 0.8, n, size=36, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        text(s, 7.0, y + 0.05, 2.6, 0.9, d, size=13, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)

    # 5 ---------------------------------------------------------- технології
    s = content_slide(prs, "Вибір технологій",
                      "Порівнював MySQL, PostgreSQL, MS SQL Server і SQLite. Обрав MySQL: "
                      "безкоштовна Community-версія, CHECK, ролі, процедури, тригери, віконні "
                      "функції і MySQL Workbench. Гілка 8.0 завершила підтримку у квітні 2026, "
                      "тому скрипти сумісні з 8.4 LTS і 9.x; перевіряв на 9.6.")
    techs = [("MySQL", "СКБД", ["CHECK, ролі, процедури, тригери, події",
                               "віконні функції та CTE",
                               "безкоштовна Community-версія"]),
             ("MySQL Workbench", "проєктування", ["EER-модель", "прямий і зворотний інжиніринг",
                                                  "синхронізація з БД"]),
             ("Python + Flask", "інтерфейс", ["PyMySQL, шаблони Jinja2",
                                              "лише CALL і SELECT з представлень",
                                              "окремий обліковий запис на роль"])]
    for i, (h, sub, items) in enumerate(techs):
        x = 0.45 + i * 3.08
        card(s, x, 1.15, 2.88, 3.05)
        text(s, x + 0.2, 1.3, 2.5, 0.45, h, size=18, bold=True, color=PURPLE)
        text(s, x + 0.2, 1.72, 2.5, 0.35, sub, size=12, color=INK)
        text(s, x + 0.2, 2.2, 2.55, 1.9, [[("•  " + t, False)] for t in items], size=13,
             color=INK, space=6)
    text(s, 0.45, 4.35, 9.1, 0.45,
         "Скрипти сумісні з MySQL 8.0, 8.4 LTS і 9.x (гілка 8.0 завершила підтримку у квітні 2026)",
         size=12, color=LILAC, align=PP_ALIGN.CENTER)

    # 6 ---------------------------------------------------------- ER-модель
    s = content_slide(prs, "Проєктування бази даних (ER-модель)",
                      "База складається з 18 таблиць. Більшість зв'язків 1:N. Зв'язок M:N між "
                      "чеками і товарами розв'язано таблицею sale_item зі складеним ключем, а "
                      "бронювання і сесія, сесія і чек за гру – це 1:1 через унікальні зовнішні ключі. Таблиці "
                      "нормалізовано до 3НФ і НФБК; свідомо збережено вартість сесії і ціну на "
                      "момент продажу.")
    picture_framed(s, IMG / "er_conceptual.png", 0.35, 1.0, h=3.85)
    pts = [("18 таблиць", "клієнти, зони, місця, тарифи, сесії, бронювання, бар, зміни, заявки, аудит"),
           ("M:N → sale_item", "чек ↔ товар зі складеним ключем і ціною продажу"),
           ("1:1", "бронювання → сесія, сесія → чек за гру; аудит → працівник"),
           ("3НФ / НФБК", "денормалізовано лише історичні суми")]
    for i, (h, d) in enumerate(pts):
        y = 1.0 + i * 0.97
        text(s, 5.75, y, 3.9, 0.36, h, size=15, bold=True)
        text(s, 5.75, y + 0.34, 3.9, 0.6, d, size=12, color=LILAC)

    # 7 ---------------------------------------------------------- логіка в СКБД
    s = content_slide(prs, "Бізнес-правила на рівні СКБД",
                      "Логіку клубу реалізують 2 функції, 5 процедур, 13 тригерів, подія і 5 "
                      "представлень. Наприклад, на одному місці не може бути двох активних сесій – це "
                      "UNIQUE на генерованому стовпці. Тригери забороняють перетин бронювань і "
                      "від'ємний баланс, змінюють статус місця і пишуть журнал аудиту.")
    stats = [("5", "процедур"), ("13", "тригерів"), ("5", "представлень"), ("30", "обмежень CHECK"),
             ("5", "ролей СКБД")]
    for i, (n, l) in enumerate(stats):
        x = 0.45 + i * 1.85
        card(s, x, 1.1, 1.7, 1.3)
        text(s, x, 1.13, 1.7, 0.75, n, size=34, bold=True, color=PURPLE, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)
        text(s, x, 1.85, 1.7, 0.45, l, size=12, color=INK, align=PP_ALIGN.CENTER)
    rules = [("Одна активна сесія на місце", "UNIQUE на генерованому стовпці active_pc"),
             ("Бронювання не перетинаються", "тригер trg_booking_bi → SIGNAL"),
             ("Баланс не стає від'ємним", "planned_end + CHECK + тригер trg_client_bu"),
             ("Баланс змінюють лише процедури", "у ролі адміністратора немає UPDATE на balance")]
    for i, (h, d) in enumerate(rules):
        x = 0.45 + (i % 2) * 4.6
        y = 2.85 + (i // 2) * 1.05
        circle_num(s, x, y + 0.08, 0.45, str(i + 1), size=14)
        text(s, x + 0.6, y, 3.9, 0.38, h, size=14, bold=True)
        text(s, x + 0.6, y + 0.36, 3.9, 0.5, d, size=12, color=LILAC)

    # 8 ---------------------------------------------------------- дані і аналітика
    s = content_slide(prs, "Тестові дані та аналітичні запити",
                      "Дані згенеровано Python-скриптом за три місяці; вони узгоджені з "
                      "правилами: сесії не перетинаються, баланси збігаються з сумою транзакцій. "
                      "Написав 19 запитів – від простих вибірок до віконних функцій і рекурсивного "
                      "CTE. На графіку – зайнятість залу за годинами, пік о 20:00.")
    n = RES["COUNTS"]
    for i, (v, l) in enumerate([(n["client"], "клієнтів"), (n["game_session"], "сесій"),
                                (n["balance_transaction"], "транзакцій"), (n["sale_bar"], "чеків бару")]):
        y = 1.05 + i * 0.92
        text(s, 0.5, y, 1.75, 0.6, f"{v:,}".replace(",", " "), size=28, bold=True,
             anchor=MSO_ANCHOR.MIDDLE)
        text(s, 2.05, y + 0.1, 1.8, 0.45, l, size=14, color=LILAC, anchor=MSO_ANCHOR.MIDDLE)
    q15 = RES["Q15"]["statements"][0]["results"][0]["rows"]
    card(s, 4.0, 1.05, 5.6, 3.7)
    cd = CategoryChartData()
    cd.categories = [f"{h}:00" for h, _ in q15]
    cd.add_series("Зайнятість, %", [float(v) for _, v in q15])
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(4.1), Inches(1.12),
                            Inches(5.4), Inches(3.56), cd)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = True
    ch.chart_title.text_frame.text = "Середня зайнятість місць за годинами, %"
    tp = ch.chart_title.text_frame.paragraphs[0]
    tp.runs[0].font.size, tp.runs[0].font.bold = Pt(12), True
    tp.runs[0].font.color.rgb, tp.runs[0].font.name = INK, FONT
    pl = ch.plots[0]
    pl.gap_width = 60
    pl.has_data_labels = True
    dl = pl.data_labels
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.name = Pt(9), FONT
    dl.font.color.rgb = INK
    dl.number_format, dl.number_format_is_linked = "0.0", False
    ser = pl.series[0]
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = PURPLE
    ca, va = ch.category_axis, ch.value_axis
    ca.tick_labels.font.size = va.tick_labels.font.size = Pt(9)
    ca.tick_labels.font.color.rgb = va.tick_labels.font.color.rgb = INK
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RGBColor(0xE4, 0xE0, 0xF0)
    va.format.line.fill.background()
    va.visible = False

    # 9 ---------------------------------------------------------- демо: зала
    s = content_slide(prs, "Демонстраційний застосунок: карта залу",
                      "Застосунок на Flask не містить бізнес-логіки: кожна кнопка викликає "
                      "процедуру або читає представлення. На карті залу місця пофарбовано за статусом "
                      "з представлення v_hall_status, видно клієнта і залишок оплаченого часу.")
    picture_framed(s, IMG / "ui_hall.png", 0.4, 0.98, h=3.95)
    items = [("Кольори місць", "вільне, зайняте, заброньоване, ремонт – з v_hall_status"),
             ("Старт і стоп сесії", "CALL sp_start_session / sp_end_session"),
             ("Поповнення", "CALL sp_top_up, бонус 5 % від 1000 грн"),
             ("Права", "кожна роль – окремий обліковий запис MySQL")]
    for i, (h, d) in enumerate(items):
        y = 1.0 + i * 0.97
        text(s, 5.2, y, 4.4, 0.36, h, size=14, bold=True)
        text(s, 5.2, y + 0.34, 4.4, 0.6, d, size=12, color=LILAC)

    # 10 --------------------------------------------------------- демо: тригер і звіти
    s = content_slide(prs, "Правила бази даних в інтерфейсі",
                      "Ліворуч – спроба забронювати зайнятий час: повідомлення сформував тригер "
                      "у базі, застосунок лише показав його. Праворуч – звіти для керуючого: "
                      "виручка за днями і зонами, найактивніші клієнти, журнал змін цін.")
    picture_framed(s, IMG / "ui_bookings.png", 0.4, 1.05, w=4.5)
    picture_framed(s, IMG / "ui_reports.png", 5.1, 1.05, w=4.5)
    text(s, 0.4, 4.05, 4.5, 0.6, "Відмова в бронюванні: повідомлення тригера БП-03",
         size=12, color=LILAC, align=PP_ALIGN.CENTER)
    text(s, 5.1, 4.05, 4.5, 0.6, "Звіти керуючого: виручка, зони, клієнти, аудит цін",
         size=12, color=LILAC, align=PP_ALIGN.CENTER)

    # 11 --------------------------------------------------------- висновки
    s = content_slide(prs, "Висновки",
                      "Усі завдання виконано. Створено базу з 18 таблиць, ролями, процедурами і "
                      "тригерами, наповнено її узгодженими даними, реалізовано запити і "
                      "демонстраційний застосунок. Подальший розвиток – інтеграція з ПЗ на "
                      "ігрових ПК, онлайн-оплата і підтримка мережі клубів. Дякую за увагу.")
    card(s, 0.45, 1.1, 5.3, 3.05)
    text(s, 0.7, 1.25, 4.9, 0.4, "Результати", size=17, bold=True, color=PURPLE)
    text(s, 0.7, 1.7, 4.9, 3.0,
         [[("•  " + t, False)] for t in [
             "Спроєктовано БД з 18 таблиць, нормалізовано до 3НФ",
             "Правила клубу реалізовано засобами СКБД",
             f"Узгоджені дані: {n['game_session']} сесій за 3 місяці",
             "19 запитів, у т. ч. віконні функції і рекурсивний CTE",
             "Вебзастосунок працює лише через процедури й представлення"]],
         size=13, color=INK, space=6)
    text(s, 6.05, 1.15, 3.6, 0.4, "Розвиток", size=17, bold=True)
    text(s, 6.05, 1.62, 3.6, 3.0,
         [[("•  " + t, False)] for t in ["Інтеграція з клієнтським ПЗ на ігрових ПК",
                                          "Онлайн-оплата поповнень",
                                          "Мережа клубів",
                                          "Перехід на MySQL 8.4 LTS"]],
         size=13, space=8)

    # 12 --------------------------------------------------------- дякую
    s = prs.slides.add_slide(L_TITLE)
    s.shapes.add_picture(str(ASSETS / "pillars.png"), Inches(5.24), Inches(0), Inches(4.65), Inches(6.22))
    s.shapes.add_picture(str(ASSETS / "logo.png"), Inches(0.39), Inches(0.45), Inches(1.66), Inches(0.4))
    text(s, 0.6, 2.3, 4.8, 0.8, "Дякую за увагу!", size=34, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 0.6, 3.1, 4.6, 0.5, "Готовий відповісти на запитання", size=15, color=LILAC)
    s.notes_slide.notes_text_frame.text = "Дякую за увагу, готовий відповісти на запитання."

    prs.core_properties.author = "Глодовський Богдан Михайлович"
    prs.core_properties.title = "БД комп'ютерного клубу – захист курсової роботи"
    prs.save(str(OUT))
    print("ok", OUT, len(prs.slides))


if __name__ == "__main__":
    build()
