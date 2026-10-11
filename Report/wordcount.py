"""Body word count as the declaration defines it. Usage, from Report/: python wordcount.py

Chapters 1 to 7, text only: tables, figures, TikZ pictures and listings are removed before counting, and
TeXcount's "Words in text" already leaves out headings and captions. Course rule (Planning/brief-compliance.md,
H6): 10 000 to 15 000 words "plus tables, diagrams and appendices"; H4: at most 50 content pages."""
import io, os, re, subprocess, tempfile

REPORT = os.path.dirname(os.path.abspath(__file__))
CHAPTERS = ["Introduction", "Literature", "Methodology", "Results", "Discussion", "Conclusions", "Recommendations"]
ENV = re.compile(r"\\begin\{(table\*?|tabular\*?|longtable|figure\*?|tikzpicture|lstlisting|verbatim)\}.*?\\end\{\1\}", re.S)


def words_in_text(path):
    out = subprocess.run(["texcount", "-q", path], capture_output=True, text=True).stdout
    m = re.search(r"Words in text: (\d+)", out)
    return int(m.group(1)) if m else 0


tmp = tempfile.mkdtemp()
tot_all = tot_text = 0
for ch in CHAPTERS:
    s = io.open(os.path.join(REPORT, ch + ".tex"), encoding="utf-8").read()
    stripped = s
    for _ in range(3):
        stripped = ENV.sub(" ", stripped)
    a = os.path.join(tmp, ch + "_all.tex"); io.open(a, "w", encoding="utf-8").write(s)
    t = os.path.join(tmp, ch + "_text.tex"); io.open(t, "w", encoding="utf-8").write(stripped)
    na, nt = words_in_text(a), words_in_text(t)
    tot_all += na; tot_text += nt
    print(f"{ch:16} with tables {na:6}  text only {nt:6}")
print(f"{'Body':16} with tables {tot_all:6}  text only {tot_text:6}")
