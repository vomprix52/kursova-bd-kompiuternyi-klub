"""Рушій збирання пояснювальної записки (python-docx).

Зміст роботи описується списком блоків (content.py); рушій нумерує рисунки,
таблиці, лістинги та джерела, підставляє посилання і форматує документ
відповідно до Положення про курсові роботи РФКІТ.
"""
import copy
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

TNR = "Times New Roman"
MONO = "Courier New"
APP_LETTERS = "АБВГДЕЖКЛМНП"
TABLE_FONT = 14   # шрифт таблиць – як в основному тексті (зауваження керівника)


# ------------------------------------------------------------------ блоки
class Content:
    def __init__(self):
        self.blocks = []

    def add(self, kind, **kw):
        self.blocks.append(dict(kind=kind, **kw))

    def h1(self, text, chapter, toc=None):
        self.add("h1", text=text, chapter=chapter, toc=toc or text)

    def h2(self, text):
        self.add("h2", text=text)

    def p(self, text, indent=True, align=None, keep=False):
        self.add("p", text=text, indent=indent, align=align, keep=keep)

    def bullets(self, items):
        for i, it in enumerate(items):
            end = "." if i == len(items) - 1 else ";"
            self.add("p", text="– " + it.rstrip(";.") + end, indent=True, align=None, keep=False)

    def table(self, key, caption, header, rows, widths, font=12, aligns=None, note=None):
        self.add("table", key=key, caption=caption, header=header, rows=rows, widths=widths,
                 font=font, aligns=aligns, note=note)

    def fig(self, key, path, caption, width=16.5):
        self.add("fig", key=key, path=path, caption=caption, width=width)

    def listing(self, key, caption, code, size=10):
        self.add("listing", key=key, caption=caption, code=code, size=size)

    def appendix(self, letter_key, title):
        self.add("app", key=letter_key, title=title)

    def pagebreak(self):
        self.add("pb")


# ------------------------------------------------------------------ XML-утиліти
# Порядок дочірніх елементів за схемою OOXML: Word 2007 не відкриває файл,
# якщо елемент стоїть не на своєму місці (новіші версії це пробачають).
AFTER = {
    "w:pBdr": ["w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
               "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
               "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
               "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
               "w:textDirection", "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl",
               "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange"],
    "w:pgNumType": ["w:cols", "w:formProt", "w:vAlign", "w:noEndnote", "w:titlePg",
                    "w:textDirection", "w:bidi", "w:rtlGutter", "w:docGrid",
                    "w:printerSettings", "w:sectPrChange"],
    "w:tblCellMar": ["w:tblLook", "w:tblCaption", "w:tblDescription", "w:tblPrChange"],
}


def insert_ordered(parent, child):
    """Вставляє child перед першим елементом, що за схемою має йти після нього."""
    tag = child.tag
    name = next(k for k in AFTER if qn(k) == tag)
    later = {qn(t) for t in AFTER[name]}
    for el in parent:
        if el.tag in later:
            el.addprevious(child)
            return child
    parent.append(child)
    return child


def fix_settings(doc):
    """У шаблоні python-docx w:zoom без обов'язкового атрибута w:percent."""
    for z in doc.settings.element.findall(qn("w:zoom")):
        if z.get(qn("w:percent")) is None:
            z.set(qn("w:percent"), "100")
def set_fonts(rpr_owner, name=TNR, size=None, bold=None):
    rpr = rpr_owner.get_or_add_rPr() if hasattr(rpr_owner, "get_or_add_rPr") else rpr_owner
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in list(rf.attrib):
        del rf.attrib[a]
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)


def run_font(run, name=TNR, size=14, bold=None, italic=None):
    run.font.name = name
    set_fonts(run._r, name)
    run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic


def add_field(paragraph, instr, cached=""):
    r1 = paragraph.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "begin")
    r1._r.append(fc)
    r2 = paragraph.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    r2._r.append(it)
    r3 = paragraph.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "separate")
    r3._r.append(fc)
    r4 = paragraph.add_run(cached)
    r5 = paragraph.add_run()
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "end")
    r5._r.append(fc)
    return [r1, r2, r3, r4, r5]


def para_fmt(p, indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, spacing=1.5, before=0, after=0,
             keep_next=False, left=None):
    f = p.paragraph_format
    f.first_line_indent = Cm(1.25) if indent else Cm(0)
    if left is not None:
        f.left_indent = Cm(left)
    f.alignment = align
    f.line_spacing = spacing
    f.space_before = Pt(before)
    f.space_after = Pt(after)
    f.keep_with_next = keep_next
    f.widow_control = True


def cell_margins(tbl, top=30, bottom=30, left=70, right=70):
    tblPr = tbl._tbl.tblPr
    m = OxmlElement("w:tblCellMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{k}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        m.append(e)
    insert_ordered(tblPr, m)


def row_flags(row, header=False):
    trPr = row._tr.get_or_add_trPr()
    cs = OxmlElement("w:cantSplit")
    trPr.append(cs)
    if header:
        th = OxmlElement("w:tblHeader")
        trPr.append(th)


APOS = re.compile(r"(?<=[А-Яа-яІіЇїЄєҐґ])'(?=[А-Яа-яІіЇїЄєҐґ])")


def prose(text):
    return APOS.sub("’", text)


# ------------------------------------------------------------------ документ
class Builder:
    def __init__(self, content, sources, splits=None, toc_entries=None, stats=None):
        self.c = content
        self.sources = sources          # список (key, text), вже відсортований
        self.src_num = {k: i + 1 for i, (k, _) in enumerate(sources)}
        self.splits = splits or {}      # key таблиці -> індекси рядків, з яких іде продовження
        self.toc_entries = toc_entries  # [(level, text, page)]
        self.push = set()               # таблиці, які варто почати з нової сторінки
        self.stats = stats or {}
        self.numbers = {}
        self.cited = set()
        self._number()

    # нумерація об'єктів у межах розділу / додатка
    def _number(self):
        chap, cnt = None, {}
        for b in self.c.blocks:
            if b["kind"] == "h1":
                chap = b["chapter"]
                cnt = {"fig": 0, "table": 0, "listing": 0}
            elif b["kind"] == "app":
                chap = APP_LETTERS[len([x for x in self.numbers if x.startswith("app:")])]
                self.numbers["app:" + b["key"]] = chap
                cnt = {"fig": 0, "table": 0, "listing": 0}
            elif b["kind"] in ("fig", "table", "listing"):
                cnt[b["kind"]] += 1
                sep = "." if chap and chap[0].isdigit() is False and chap in APP_LETTERS else "."
                self.numbers[f"{b['kind']}:{b['key']}"] = f"{chap}{sep}{cnt[b['kind']]}"
        self.counts = {k: sum(1 for b in self.c.blocks if b["kind"] == k
                              and self._in_main(b)) for k in ("fig", "table", "listing")}

    def _in_main(self, b):
        n = self.numbers.get(f"{b['kind']}:{b.get('key')}", "")
        return n[:1].isdigit()

    def ref(self, text):
        def sub(m):
            kind, key = m.group(1), m.group(2)
            if kind == "src":
                out = []
                for part in key.split(","):
                    k, _, pg = part.partition("@")
                    if k not in self.src_num:
                        raise KeyError(f"невідоме джерело {k}")
                    self.cited.add(k)
                    out.append(f"{self.src_num[k]}" + (f", с. {pg}" if pg else ""))
                return "[" + "; ".join(out) + "]"
            if kind == "stat":
                return str(self.stats.get(key, "??"))
            full = {"fig": "fig", "tab": "table", "lst": "listing", "app": "app"}[kind] + ":" + key
            if full not in self.numbers:
                raise KeyError(f"невідоме посилання {full}")
            return self.numbers[full]
        return re.sub(r"\{(fig|tab|lst|src|stat|app):([^}]+)\}", sub, text)

    # ---------------------------------------------------------- стилі
    def _styles(self, doc):
        st = doc.styles
        normal = st["Normal"]
        normal.font.name = TNR
        normal.font.size = Pt(14)
        set_fonts(normal.element.get_or_add_rPr())
        lang = OxmlElement("w:lang")
        lang.set(qn("w:val"), "uk-UA")
        normal.element.get_or_add_rPr().append(lang)
        pf = normal.paragraph_format
        pf.line_spacing = 1.5
        pf.first_line_indent = Cm(1.25)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        for name, center in (("Heading 1", True), ("Heading 2", False)):
            s = st[name]
            s.font.name = TNR
            set_fonts(s.element.get_or_add_rPr())
            s.font.size = Pt(14)
            s.font.bold = True
            s.font.italic = False
            s.font.color.rgb = RGBColor(0, 0, 0)
            f = s.paragraph_format
            f.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.JUSTIFY
            f.first_line_indent = Cm(0) if center else Cm(1.25)
            f.left_indent = Cm(0)
            f.line_spacing = 1.5
            f.space_before = Pt(0) if center else Pt(12)
            f.space_after = Pt(12) if center else Pt(6)
            f.keep_with_next = True
            f.page_break_before = center
        for lvl in (1, 2):
            try:
                s = st[f"toc {lvl}"]
            except KeyError:
                from docx.enum.style import WD_STYLE_TYPE
                s = st.add_style(f"toc {lvl}", WD_STYLE_TYPE.PARAGRAPH)
            s.base_style = normal
            f = s.paragraph_format
            f.first_line_indent = Cm(0)
            f.left_indent = Cm(0 if lvl == 1 else 0.6)
            f.alignment = WD_ALIGN_PARAGRAPH.LEFT
            f.line_spacing = 1.5
            f.tab_stops.add_tab_stop(Cm(17), alignment=2, leader=1)  # right, dots

    # ---------------------------------------------------------- титул і завдання
    def _title(self, doc, template_path, data):
        tpl = Document(template_path)
        body = doc.element.body
        anchor = body[0] if len(body) else None
        for el in tpl.element.body:
            if el.tag == qn("w:sectPr"):
                continue
            new = copy.deepcopy(el)
            if anchor is not None:
                anchor.addprevious(new)
            else:
                body.append(new)
        paras = doc.paragraphs[:len([e for e in tpl.element.body if e.tag == qn("w:p")])]
        for p in paras:
            ind = p._p.pPr.find(qn("w:ind")) if p._p.pPr is not None else None
            if ind is None:
                ind = OxmlElement("w:ind")
                p._p.get_or_add_pPr().append(ind)
            if ind.get(qn("w:firstLine")) is None and ind.get(qn("w:hanging")) is None:
                ind.set(qn("w:firstLine"), "0")
            for r in p.runs:
                set_fonts(r._r.get_or_add_rPr())
        return paras

    # ---------------------------------------------------------- побудова
    def build(self, path, title_template, title_fill, task_fn):
        doc = Document()
        self._styles(doc)
        sec = doc.sections[0]
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        sec.top_margin = sec.bottom_margin = Cm(2)
        sec.left_margin, sec.right_margin = Cm(3), Cm(1)
        sec.header_distance = Cm(1.0)

        front = bool(title_template or task_fn)
        if title_template:
            paras = self._title(doc, title_template, title_fill)
            title_fill(paras)
        if task_fn:
            task_fn(self, doc)

        # Титул (окремий файл) і завдання не входять у нумерацію (вимога керівника):
        # зміст – сторінка 1 з номером, далі нумерація наскрізна.
        if front:
            toc_sec = doc.add_section(WD_SECTION.NEW_PAGE)
            for el in toc_sec._sectPr.findall(qn("w:pgNumType")):
                toc_sec._sectPr.remove(el)
            doc.sections[0].header.is_linked_to_previous = False
        else:
            toc_sec = sec
        pg = OxmlElement("w:pgNumType")
        pg.set(qn("w:start"), "1")
        insert_ordered(toc_sec._sectPr, pg)
        toc_sec.header.is_linked_to_previous = False
        hp = toc_sec.header.paragraphs[0]
        para_fmt(hp, indent=False, align=WD_ALIGN_PARAGRAPH.RIGHT, spacing=1.0)
        for r in add_field(hp, "PAGE", "1"):
            run_font(r)
        self._toc(doc)

        # розділ 3: основна частина, нумерація продовжується
        new = doc.add_section(WD_SECTION.NEW_PAGE)
        for el in new._sectPr.findall(qn("w:pgNumType")):
            new._sectPr.remove(el)
        new.header.is_linked_to_previous = True

        first_h1 = True
        for b in self.c.blocks:
            getattr(self, "_" + b["kind"])(doc, b, first_h1)
            if b["kind"] == "h1":
                first_h1 = False
        fix_settings(doc)
        doc.save(path)
        return self

    # ---------------------------------------------------------- зміст
    def _toc(self, doc):
        h = doc.add_paragraph()
        para_fmt(h, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)
        h.paragraph_format.page_break_before = False   # зміст починає власний розділ
        run_font(h.add_run("ЗМІСТ"), bold=True)
        entries = self.toc_entries or [(1, "Зміст буде оновлено", "")]
        first = doc.add_paragraph(style="toc 1")
        runs = add_field(first, 'TOC \\o "1-2" \\h \\z \\u', "")
        for r in runs:
            run_font(r)
        # кешований вміст поля: перший запис у тому ж абзаці
        fld_end = runs[4]._r
        runs[3]._r.getparent().remove(runs[3]._r)
        paras = [first]
        for i, (lvl, text, page) in enumerate(entries):
            p = first if i == 0 else doc.add_paragraph(style=f"toc {lvl}")
            if i == 0:
                p.style = doc.styles[f"toc {lvl}"]
                r = OxmlElement("w:r")
                fld_end.addprevious(r)
                from docx.text.run import Run
                run = Run(r, p)
                run.text = f"{text}\t{page}"
                run_font(run)
            else:
                run_font(p.add_run(f"{text}\t{page}"))
            paras.append(p)
        # перенести кінець поля в останній абзац
        if len(entries) > 1:
            paras[-1]._p.append(fld_end)

    # ---------------------------------------------------------- блоки
    def _h1(self, doc, b, first):
        p = doc.add_paragraph(style="Heading 1")
        if first:
            p.paragraph_format.page_break_before = False
        run_font(p.add_run(b["text"]), bold=True)

    def _h2(self, doc, b, first):
        p = doc.add_paragraph(style="Heading 2")
        run_font(p.add_run(b["text"]), bold=True)

    def _app(self, doc, b, first):
        letter = self.numbers["app:" + b["key"]]
        p = doc.add_paragraph(style="Heading 1")
        run_font(p.add_run(f"Додаток {letter}"), bold=True)
        p.runs[0].add_break()
        run_font(p.add_run(b["title"]), bold=True)

    def _pb(self, doc, b, first):
        doc.add_paragraph().runs or doc.paragraphs[-1].add_run().add_break(WD_BREAK.PAGE)

    def _p(self, doc, b, first):
        p = doc.add_paragraph()
        align = b.get("align") or WD_ALIGN_PARAGRAPH.JUSTIFY
        para_fmt(p, indent=b.get("indent", True), align=align, keep_next=b.get("keep", False))
        text = prose(self.ref(b["text"]))
        for i, part in enumerate(re.split(r"\*\*", text)):
            if part:
                run_font(p.add_run(part), bold=(i % 2 == 1))

    def _caption(self, doc, text, center, keep):
        p = doc.add_paragraph()
        para_fmt(p, indent=False,
                 align=WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT,
                 keep_next=keep, before=0 if keep else 0, after=0 if keep else 6)
        run_font(p.add_run(prose(text)))
        return p

    def _fig(self, doc, b, first):
        num = self.numbers["fig:" + b["key"]]
        p = doc.add_paragraph()
        para_fmt(p, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0, before=6,
                 keep_next=True)
        p.add_run().add_picture(str(b["path"]), width=Cm(b["width"]))
        self._caption(doc, f"Рисунок {num} – {b['caption']}", True, False).paragraph_format.space_after = Pt(6)

    def _listing(self, doc, b, first):
        num = self.numbers["listing:" + b["key"]]
        cap = self._caption(doc, f"Лістинг {num} – {b['caption']}", False, True)
        cap.paragraph_format.space_before = Pt(6)
        lines = b["code"].rstrip("\n").split("\n")
        p = doc.add_paragraph()
        para_fmt(p, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0, after=6)
        pPr = p._p.get_or_add_pPr()
        bdr = OxmlElement("w:pBdr")
        for side in ("top", "left", "bottom", "right"):
            e = OxmlElement(f"w:{side}")
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), "4")
            e.set(qn("w:space"), "4")
            e.set(qn("w:color"), "808080")
            bdr.append(e)
        insert_ordered(pPr, bdr)
        for i, line in enumerate(lines):
            r = p.add_run(line)
            run_font(r, MONO, b["size"])
            if i < len(lines) - 1:
                r.add_break()

    def _table(self, doc, b, first):
        num = self.numbers["table:" + b["key"]]
        rows = [[self.ref(str(c)) for c in r] for r in b["rows"]]
        header = b["header"]
        splits = sorted(self.splits.get(b["key"], []))
        chunks, start = [], 0
        for s in splits + [len(rows)]:
            chunks.append(rows[start:s])
            start = s
        for ci, chunk in enumerate(chunks):
            if ci == 0:
                cp = self._caption(doc, f"Таблиця {num} – {b['caption']}", False, True)
                if b["key"] in self.push:
                    cp.paragraph_format.page_break_before = True
            else:
                self._caption(doc, f"Продовження таблиці {num}", False, True)
            self._table_part(doc, b, header, chunk, last=(ci == len(chunks) - 1))
        if b.get("note"):
            p = doc.add_paragraph()
            para_fmt(p, indent=True, spacing=1.0, after=6)
            run_font(p.add_run(prose(self.ref(b["note"]))), size=12)

    def _table_part(self, doc, b, header, rows, last):
        t = doc.add_table(rows=1 + len(rows), cols=len(header))
        t.style = doc.styles["Table Grid"]
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        cell_margins(t)
        for ci, w in enumerate(b["widths"]):
            t.columns[ci].width = Cm(w)
        aligns = b.get("aligns") or ["l"] * len(header)
        keep_all = len(rows) <= 8
        for ri, data in enumerate([header] + rows):
            row = t.rows[ri]
            row_flags(row, header=(ri == 0))
            for ci, val in enumerate(data):
                cell = row.cells[ci]
                cell.width = Cm(b["widths"][ci])
                p = cell.paragraphs[0]
                a = "c" if ri == 0 else aligns[ci]
                para_fmt(p, indent=False, spacing=1.0,
                         align={"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER,
                                "r": WD_ALIGN_PARAGRAPH.RIGHT, "j": WD_ALIGN_PARAGRAPH.LEFT}[a],
                         keep_next=ri < len(rows) and (keep_all or ri <= 1))  # заголовок не відривається від даних
                txt = str(val)
                mono = txt.startswith("`") and txt.endswith("`") and len(txt) > 1
                if mono:
                    txt = txt[1:-1]
                else:
                    txt = prose(txt)
                for k, part in enumerate(re.split(r"\*\*", txt)):
                    if part:
                        r = p.add_run(part)
                        run_font(r, MONO if mono else TNR,
                                 TABLE_FONT - (1 if mono else 0), bold=(ri == 0 or k % 2 == 1))
        if not last:
            return
        # абзац-відступ після таблиці
        sp = doc.add_paragraph()
        para_fmt(sp, indent=False, spacing=1.0)
        sp.paragraph_format.space_after = Pt(0)
        r = sp.add_run("")
        run_font(r, size=6)
