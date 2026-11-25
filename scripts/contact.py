"""Контактні аркуші сторінок PDF для візуальної перевірки."""
import sys
import pymupdf
from PIL import Image
pdf, start, end, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 4
d = pymupdf.open(pdf)
ims = []
for i in range(start - 1, min(end, d.page_count)):
    pix = d[i].get_pixmap(dpi=int(sys.argv[6]) if len(sys.argv) > 6 else 45)
    ims.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (w + 8), rows * (h + 8)), "gray")
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * (w + 8), (k // cols) * (h + 8)))
sheet.save(out)
print(sheet.size)
