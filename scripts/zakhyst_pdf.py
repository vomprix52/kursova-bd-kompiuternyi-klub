"""docs/<name>.md -> docs/<name>.pdf (за замовчуванням Zakhyst) (формат A5 – зручно читати з телефона)."""
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
import sys
NAME = sys.argv[1] if len(sys.argv) > 1 else "Zakhyst"
md = (ROOT / "docs" / f"{NAME}.md").read_text(encoding="utf-8")
body = markdown.markdown(md, extensions=["fenced_code", "tables", "sane_lists", "nl2br"])
html = f"""<!doctype html><html lang="uk"><head><meta charset="utf-8"><style>
@page {{ size: A5; margin: 12mm 11mm 14mm; }}
body {{ font: 11.5pt/1.45 "Segoe UI", Arial, sans-serif; color: #1d2433; }}
h1 {{ font-size: 17pt; margin: 0 0 6pt; }}
h2 {{ font-size: 14pt; margin: 16pt 0 6pt; padding-bottom: 3pt; border-bottom: 1px solid #ccd; }}
h3 {{ font-size: 12pt; margin: 12pt 0 4pt; }}
p, li {{ margin: 0 0 6pt; }}
ol, ul {{ padding-left: 16pt; }}
code {{ font: 9.5pt Consolas, "Courier New", monospace; background: #f1f3f8; padding: 0 2pt; border-radius: 3px; }}
pre {{ background: #f1f3f8; padding: 6pt 8pt; border-radius: 4px; white-space: pre-wrap; word-break: break-all; }}
pre code {{ background: none; padding: 0; }}
hr {{ border: 0; border-top: 1px solid #ccd; margin: 12pt 0; }}
strong {{ color: #111; }}
</style></head><body>{body}</body></html>"""
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.set_content(html, wait_until="load")
    page.pdf(path=str(ROOT / "docs" / f"{NAME}.pdf"), format="A5", print_background=True,
             display_header_footer=True, header_template="<span></span>",
             footer_template='<div style="font-size:8pt;width:100%;text-align:center;color:#889">'
                             '<span class="pageNumber"></span> / <span class="totalPages"></span></div>',
             margin={"top": "12mm", "bottom": "14mm", "left": "11mm", "right": "11mm"})
    b.close()
print("ok")
