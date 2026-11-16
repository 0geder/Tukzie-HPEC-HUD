"""Speaker script PDF: one A4 page per slide, slide image on top and its talking points below."""
import re, sys, html
import pymupdf

DECK, MD, OUT = sys.argv[1:4]
md = open(MD, encoding="utf-8").read()
blocks = re.findall(r"^## Slide (\d+): (.*?) \((\d+) words, about (\d+) s\)\n\n(.*?)(?=\n## |\Z)", md, re.S | re.M)
deck = pymupdf.open(DECK)
out = pymupdf.open()
W, H = pymupdf.paper_size("a4")
M = 50
total_w = sum(int(b[2]) for b in blocks)
total_s = sum(int(b[3]) for b in blocks)
cum = 0
CSS = "body{font-family:sans-serif;font-size:12.5pt;line-height:1.45;color:#1a1a1a} h1{font-size:15pt;color:#14305C;margin:0 0 4pt 0} .m{font-size:9.5pt;color:#666;margin:0 0 8pt 0}"
for n, title, words, secs, text in blocks:
    n = int(n)
    page = out.new_page(width=W, height=H)
    src = deck[n - 1]
    iw = W - 2 * M
    ih = iw * src.rect.height / src.rect.width
    page.show_pdf_page(pymupdf.Rect(M, M, M + iw, M + ih), deck, n - 1)
    page.draw_rect(pymupdf.Rect(M, M, M + iw, M + ih), color=(0.75, 0.78, 0.85), width=0.6)
    start = cum
    cum += int(secs)
    body = (f"<h1>Slide {n}: {html.escape(title)}</h1>"
            f"<p class='m'>{words} words, about {secs} s &nbsp;|&nbsp; from {start // 60}:{start % 60:02d} to {cum // 60}:{cum % 60:02d}</p>"
            f"<p>{html.escape(text.strip())}</p>")
    page.insert_htmlbox(pymupdf.Rect(M, M + ih + 18, W - M, H - M), body, css=CSS)
    page.insert_text((W - M - 120, H - 25), f"Speaker script  |  {n} of {len(blocks)}", fontsize=8, color=(0.5, 0.5, 0.5))
out.set_metadata({"title": "SW-7 final presentation: speaker script"})
out.save(OUT)
print(len(blocks), "slides,", total_w, "words, about", round(total_s / 60, 1), "min")
