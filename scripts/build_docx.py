"""Збирання docs/Kursova_BD_Kompiuternyi_klub.docx у кілька проходів:
1) збирання -> 2) PDF через LibreOffice -> 3) номери сторінок для змісту,
місця перенесення таблиць («Продовження таблиці»), статистика -> повтор."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pymupdf
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Pt

sys.path.insert(0, str(Path(__file__).parent))
import content as C  # noqa: E402
from docx_engine import Builder, para_fmt, run_font, prose  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "Kursova_BD_Kompiuternyi_klub.docx"
TMP = ROOT / "docs" / "tmp"
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"
TEMPLATE = Path(r"C:\Users\kracu\Downloads\титулка.docx")
if not TEMPLATE.exists():
    TEMPLATE = TMP / "title_template.docx"

UNNUMBERED = 0   # титул – окремий файл, завдання прибрано: перша сторінка – зміст
STUDENT = "Глодовський Богдан Михайлович"
STUDENT_GEN = "Глодовського Богдана Михайловича"
GROUP = "ІПЗ 3/2"
SPEC = "121 «Інженерія програмного забезпечення»"
SUPERVISOR = "Лагоднюк Д. О."
SUPERVISOR_SIGN = "Д. О. ЛАГОДНЮК"


def title_fill(paras):
    def set_runs(p, texts):
        for r, t in zip(p.runs, texts):
            r.text = t
    topic = prose(f"на тему «{C.TOPIC}»")
    p = paras[15]
    p.runs[0].text = topic
    for r in p.runs[1:]:
        r.text = ""
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p23 = paras[23]
    p23.runs[2].text = GROUP
    p25 = paras[25]
    p25.runs[2].text = prose("121 «Інженерія програмного забезпечення»")
    p25.runs[2].font.size = Pt(12)
    # ПІБ над лінією «(прізвище, ім'я, по батькові ...)»
    r = paras[26].add_run(STUDENT)
    run_font(r, size=13, bold=True)
    p29 = paras[29]
    p29.runs[3].text = " " + SUPERVISOR
    p29.runs[3].font.underline = True
    paras[38].runs[1].text = "26"
    # прибрати кілька порожніх рядків, щоб титул уміщався на одну сторінку
    for i in (36, 19, 18, 17):
        el = paras[i]._p
        el.getparent().remove(el)


def task_page(builder, doc):
    def para(text, align=WD_ALIGN_PARAGRAPH.LEFT, bold=False, size=12, before=0, after=0,
             first=False, indent=0.0):
        p = doc.add_paragraph()
        para_fmt(p, indent=False, align=align, spacing=1.0, before=before, after=after)
        if indent:
            p.paragraph_format.left_indent = __import__("docx").shared.Cm(indent)
        if first:
            p.paragraph_format.page_break_before = True
        for i, part in enumerate(re.split(r"\*\*", prose(text))):
            if part:
                run_font(p.add_run(part), size=size, bold=bold or i % 2 == 1)
        return p

    C_ = WD_ALIGN_PARAGRAPH.CENTER
    para("МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ", C_, True, first=True)
    para("РІВНЕНСЬКИЙ ФАХОВИЙ КОЛЕДЖ ІНФОРМАЦІЙНИХ ТЕХНОЛОГІЙ", C_, True)
    para("Циклова комісія інформаційних технологій та інженерії", C_, before=6)
    para(f"Спеціальність: {SPEC}", C_)
    para("ЗАВДАННЯ", C_, True, size=14, before=14)
    para("для виконання курсової роботи з дисципліни «Бази даних»", C_)
    para(f"здобувача освіти 3 курсу, групи {GROUP}", C_)
    para(STUDENT_GEN, C_, True)
    para("Тема курсової роботи", C_, before=6)
    para(f"«{C.TOPIC}»", C_, True)
    para("При виконанні курсової роботи необхідно розкрити наступні завдання:", C_, before=8, after=4)
    para("Вступ")
    for _, _, title, subs in C.SUBSECTIONS:
        para(title)
        for s in subs:
            para(s, indent=0.6)
    para("Висновки та пропозиції")
    para("Список використаних джерел")
    para("Додатки")
    para("Перелік додатків", C_, True, before=6, after=2)
    for i, (key, title) in enumerate(C.APPENDICES):
        para(f"Додаток {'АБВГДЕЖ'[i]} – {title}")
    para("Дата видачі завдання «___» ______________ 2026 року", before=14)
    para("Керівник курсової роботи  ______________  " + SUPERVISOR_SIGN, before=8)
    para("(підпис)", size=9, indent=5.2)
    para("Завдання до виконання прийняв «___» ______________ 2026 року  ______________",
         before=8)
    para("(підпис здобувача освіти)", size=9, indent=11.3)


class KBuilder(Builder):
    def _pb(self, doc, b, first):
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def _sources(self, doc, b, first):
        for i, (key, text) in enumerate(self.sources, 1):
            p = doc.add_paragraph()
            para_fmt(p, indent=True)
            run_font(p.add_run(f"{i}. " + prose(text)))

    def _review(self, doc, b, first):
        def para(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, before=0, indent=True):
            p = doc.add_paragraph()
            para_fmt(p, indent=indent, align=align, spacing=1.15, before=before)
            for i, part in enumerate(re.split(r"\*\*", prose(text))):
                if part:
                    run_font(p.add_run(part), size=13, bold=bold or i % 2 == 1)
            return p
        C_ = WD_ALIGN_PARAGRAPH.CENTER
        para("РЕЦЕНЗІЯ", C_, True, indent=False).paragraph_format.page_break_before = True
        para("керівника курсової роботи", C_, indent=False)
        para("з дисципліни «Бази даних» про якість і готовність роботи до захисту", C_, indent=False)
        para(f"Курсову роботу виконав здобувач освіти 3 курсу, групи {GROUP} "
             f"{STUDENT} на тему: «{C.TOPIC}».", before=8)
        para(f"1. Курсову роботу виконано у відповідності з вимогами методичних рекомендацій "
             f"для спеціальності: {SPEC}. Курсова робота складається з наступних розділів:")
        for _, _, title, subs in C.SUBSECTIONS:
            para(title + " (" + "; ".join(s.split(". ", 1)[0] for s in subs) + ").")
        para("2. Розгорнутість та аналітичний зміст теоретичної частини курсової роботи з "
             "додатками за критеріями оцінювання відповідає оцінці «5» (відмінно), «4» (добре), "
             "«3» (задовільно), «2» (незадовільно).")
        para("3. Актуальність, структурно-логічна послідовність та обґрунтованість практичної "
             "частини курсової роботи, наявність аналітичної складової та/або додатків "
             "заслуговує оцінки «5» (відмінно), «4» (добре), «3» (задовільно), «2» (незадовільно).")
        para("4. Сильні сторони: " + "_" * 52, WD_ALIGN_PARAGRAPH.LEFT)
        para("_" * 70, WD_ALIGN_PARAGRAPH.LEFT, indent=False)
        para("5. Слабкі сторони: " + "_" * 52, WD_ALIGN_PARAGRAPH.LEFT)
        para("_" * 70, WD_ALIGN_PARAGRAPH.LEFT, indent=False)
        para("6. Висновки: курсову роботу допущено до захисту та рекомендовано на оцінку "
             "«____» (______________).")
        para("7. Відмітка про загальну оцінку курсової роботи з урахуванням захисту перед "
             "комісією навчального закладу: «____» (______________).")
        para("Дата захисту «___» ______________ 2026 р.", before=8)
        para(f"Керівник курсової роботи: ______________ {SUPERVISOR_SIGN}", before=8)


def toc_entries(content, pages=None):
    out = []
    for b in content.blocks:
        if b["kind"] == "h1":
            out.append((1, b["toc"], b["text"]))
        elif b["kind"] == "h2":
            out.append((2, b["text"], b["text"]))
        elif b["kind"] == "app":
            out.append((1, None, b))
    res, letters = [], iter("АБВГДЕЖКЛМН")
    for lvl, text, raw in out:
        if text is None:
            letter = next(letters)
            text = f"Додаток {letter}. {raw['title']}"
            raw = f"Додаток {letter}"
        res.append([lvl, prose(text), raw])
    return res


def render_pdf(docx_path):
    subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(TMP),
                    str(docx_path)], check=True, capture_output=True)
    return TMP / (docx_path.stem + ".pdf")


def norm(s):
    s = s.replace("’", "'").replace("ʼ", "'").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def analyse(pdf_path, entries, builder):
    doc = pymupdf.open(pdf_path)
    pages = [norm(p.get_text()) for p in doc]
    # сторінка змісту: шукаємо заголовки після неї
    start = next(i for i, t in enumerate(pages) if t.startswith("вступ") or "\nвступ" in t
                 or re.match(r"^(\d+ )?вступ ", t)) if False else 0
    toc_page = next(i for i, t in enumerate(pages) if "зміст" in t[:40])
    pos = toc_page + 1
    while "вступ" not in pages[pos][:40]:
        pos += 1
    found = []
    for lvl, text, raw in entries:
        key = norm(raw if isinstance(raw, str) else text)[:45]
        i = pos
        while i < len(pages) and key not in pages[i]:
            i += 1
        if i == len(pages):
            raise SystemExit(f"не знайдено заголовок: {key}")
        found.append(i + 1 - UNNUMBERED)
        pos = i
    # таблиці: визначаємо, з якого рядка таблиця переходить на наступну сторінку
    splits, pushes = {}, set()
    pos = toc_page + 1
    for b in builder.c.blocks:
        if b["kind"] != "table":
            continue
        num = builder.numbers["table:" + b["key"]]
        cap = norm(f"Таблиця {num} – {b['caption']}")[:40]
        i = pos
        while i < len(pages) and cap not in pages[i]:
            i += 1
        if i == len(pages):
            continue
        # стовпець-ідентифікатор рядка: перший стовпець з унікальними значеннями
        col = 0
        for ci in range(min(3, len(b["header"]))):
            vals = [norm(str(r[ci]).strip("`"))[:14] for r in b["rows"]]
            if len(set(vals)) == len(vals) and min(len(v) for v in vals) >= 3:
                col = ci
                break
        cur_page, last_off = i, pages[i].find(cap)
        for ri, row in enumerate(b["rows"]):
            k = norm(str(row[col]).strip("`"))[:14]
            off = pages[cur_page].find(k, last_off) if k else -1
            if off >= 0:
                last_off = off
                continue
            nxt = cur_page + 1
            if k and nxt < len(pages) and pages[nxt].find(k) >= 0:
                if 0 < ri <= 2 and not splits.get(b["key"]):
                    pushes.add(b["key"])      # на старій сторінці лишилось 1–2 рядки
                elif ri > 0:
                    splits.setdefault(b["key"], []).append(ri)
                cur_page, last_off = nxt, pages[nxt].find(k)
        pos = cur_page
    total = len(pages) - UNNUMBERED
    intro = found[0]
    src_page = next(f for (lvl, t, r), f in zip(entries, found) if t.startswith("СПИСОК"))
    stats = dict(main_pages=src_page - intro, total_pages=total)
    return found, splits, stats, pushes


def build_title():
    """Титульний аркуш окремим файлом на основі шаблону коледжу."""
    from docx import Document
    from docx.shared import Cm
    doc = Document(TEMPLATE)
    title_fill(doc.paragraphs)
    for sec in doc.sections:
        sec.left_margin, sec.right_margin = Cm(3), Cm(1)
        sec.top_margin = sec.bottom_margin = Cm(2)
    path = ROOT / "docs" / "Tytulka.docx"
    from docx_engine import fix_settings
    fix_settings(doc)
    doc.save(path)
    pdf = render_pdf(path)
    n = pymupdf.open(pdf).page_count
    print("титулка:", path, "сторінок:", n)


def build_review():
    """Бланк рецензії (Додаток 2 Положення) окремим файлом."""
    from docx import Document
    from docx.shared import Cm
    from docx_engine import set_fonts
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(3), Cm(1)
    sec.top_margin = sec.bottom_margin = Cm(2)
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    set_fonts(st.element.get_or_add_rPr())
    KBuilder._review(None, doc, None, None)
    doc.paragraphs[0].paragraph_format.page_break_before = False
    path = ROOT / "docs" / "Retsenziia.docx"
    from docx_engine import fix_settings
    fix_settings(doc)
    doc.save(path)
    print("рецензія:", path)


def main():
    TMP.mkdir(exist_ok=True)
    build_title()
    build_review()
    content = C.build_content()
    sources = C.sorted_sources()
    entries = toc_entries(content)
    stats = dict(sources=len(sources), apps=len(C.APPENDICES), main_pages="??",
                 total_pages="??")
    splits, pages, push = {}, [""] * len(entries), set()
    for it in range(7):
        b = KBuilder(content, sources, splits=splits,
                     toc_entries=[(lvl, t, p) for (lvl, t, _), p in zip(entries, pages)],
                     stats=stats)
        b.stats.update(figs=b.counts["fig"], tabs=b.counts["table"])
        b.push = set(push)
        b.build(OUT, None, title_fill, None)
        unused = set(C.SOURCES) - b.cited
        if unused:
            print("УВАГА: джерела без посилань:", unused)
        pdf = render_pdf(OUT)
        new_pages, new_splits, st, new_push = analyse(pdf, entries, b)
        changed_push = not new_push <= push
        push |= new_push
        changed = (changed_push or new_pages != pages or new_splits != splits
                   or st["main_pages"] != stats["main_pages"]
                   or st["total_pages"] != stats["total_pages"])
        pages, splits = new_pages, new_splits
        stats.update(st)
        print(f"прохід {it + 1}: основна частина {st['main_pages']} с., усього {st['total_pages']} с., "
              f"переноси таблиць: {splits}, з нової сторінки: {sorted(push)}")
        if not changed:
            break
    (TMP / "build_info.json").write_text(json.dumps(dict(stats=stats, pages=pages,
                                                         entries=[e[:2] for e in entries]),
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    print("готово:", OUT)


if __name__ == "__main__":
    main()
