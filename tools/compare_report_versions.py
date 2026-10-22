"""Check that a shortened report kept the information of an earlier version.

Compares two compiled PDFs (old, new) and the LaTeX sources of the new one:
  1. every number in the old PDF still appears in the new PDF (anywhere, body or appendix);
  2. every figure, table and equation label and every citation key of the old sources still exists in the new;
  3. counts of figures, tables and citations, old and new.
Usage: python tools/compare_report_versions.py OLD.pdf NEW.pdf OLD_SRC_DIR_OR_GIT_REF NEW_SRC_DIR
(OLD_SRC as a git ref, e.g. report-pre-length-cut-2026-10-22, reads Report/*.tex from that commit.)
"""
import re, sys, os, subprocess, collections
import pymupdf

def pdf_text(p):
    d = pymupdf.open(p)
    return "\n".join(pg.get_text() for pg in d), len(d)

NUM = re.compile(r"(?<![\w.])[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])[-+]?\d+\.\d+|(?<![\w.,])\d{2,}(?![\w])")

def numbers(text):
    t = text.replace("\u2212", "-").replace("\u2009", "").replace("\u202f", "")
    return collections.Counter(m.group(0).lstrip("+") for m in NUM.finditer(t))

def tex_sources(src):
    if os.path.isdir(src):
        files = {f: open(os.path.join(src, f), encoding="utf-8", errors="replace").read()
                 for f in os.listdir(src) if f.endswith(".tex")}
    else:
        names = subprocess.run(["git", "ls-tree", "--name-only", src, "Report/"], capture_output=True, text=True).stdout.split()
        files = {n.split("/")[-1]: subprocess.run(["git", "show", f"{src}:{n}"], capture_output=True, text=True,
                 encoding="utf-8", errors="replace").stdout for n in names if n.endswith(".tex")}
    return "\n".join(files.values())

def keys(tex):
    labels = set(re.findall(r"\\label\{([^}]+)\}", tex))
    cites = set(k.strip() for grp in re.findall(r"\\cite\{([^}]+)\}", tex) for k in grp.split(","))
    figs = len(re.findall(r"\\begin\{figure\}", tex)); tabs = len(re.findall(r"\\begin\{(?:table|longtable)\}", tex))
    return labels, cites, figs, tabs

old_pdf, new_pdf, old_src, new_src = sys.argv[1:5]
ot, on = pdf_text(old_pdf); nt, nn = pdf_text(new_pdf)
oN, nN = numbers(ot), numbers(nt)
missing = sorted(k for k in oN if k not in nN)
print(f"PDF pages: old {on}, new {nn}")
print(f"distinct numbers: old {len(oN)}, new {len(nN)}; in old but not in new: {len(missing)}")
for k in missing:
    i = ot.replace("\u2212", "-").find(k)
    ctx = ot[max(0, i - 70): i + 50].replace("\n", " ") if i >= 0 else ""
    print(f"  MISSING {k!r}: ...{ctx}...")
OL, OC, OF, OT = keys(tex_sources(old_src)); NL, NC, NF, NT = keys(tex_sources(new_src))
print(f"labels: old {len(OL)}, new {len(NL)}; lost: {sorted(OL - NL)}")
print(f"citation keys: old {len(OC)}, new {len(NC)}; lost: {sorted(OC - NC)}")
print(f"figure environments: old {OF}, new {NF}; table environments: old {OT}, new {NT}")
