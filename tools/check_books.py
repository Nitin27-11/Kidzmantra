"""Check every book in public/books against the chapter lists on the site.

Reports missing chapters, quizzes with broken lines, questions without
answers, sections with nothing in them and pictures that don't exist. With
--render it also runs the site's own book renderer over every chapter (macOS,
through osascript) to catch anything that fails to display.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PUBLIC = Path(__file__).resolve().parent.parent / "public"
BOOKS = PUBLIC / "books"
IMG = BOOKS / "img"


def chapter_titles():
    src = (PUBLIC / "index.html").read_text()
    grades = src[src.index("const GRADES=["):]
    grades = grades[:grades.index("\n];")]
    titles = {}
    for g in re.finditer(r'\{id:"([\w-]+)".*?s:\{(.*?)\}\}', grades, re.S):
        for s in re.finditer(r'(\w+):"(.*?)"', g.group(2)):
            titles[(g.group(1), s.group(1))] = s.group(2).split("|")
    return titles


def chapters(path):
    out, n = {}, None
    for line in path.read_text().splitlines():
        if m := re.match(r"^@@\s*(\d+)\s*$", line):
            n = int(m.group(1))
            out[n] = []
        elif n is not None:
            out[n].append(line.strip())
    return out


def check_chapter(where, lines):
    problems, quiz, section, filled, waiting = [], 0, None, True, False
    for line in lines + ["## end"]:
        if line.startswith("## "):
            if section is not None and not filled:
                problems.append(f"{where}: section '{section}' is empty")
            section, filled = line[3:], False
            continue
        if line:
            filled = True
        if m := re.match(r"^(MCQ|TF|FILL):\s*(.*)", line):
            quiz += 1
            kind, body = m.group(1), m.group(2).split("||")[0]
            parts = [p.strip() for p in body.split("|")]
            if kind == "MCQ" and sum(p.startswith("*") for p in parts[1:]) != 1:
                problems.append(f"{where}: MCQ needs exactly one *right option: {line[:60]}")
            if kind == "TF" and (len(parts) != 2 or parts[1].lower() not in ("true", "false")):
                problems.append(f"{where}: TF needs 'true' or 'false': {line[:60]}")
            if kind == "FILL" and (len(parts) != 2 or "___" not in parts[0] or not parts[1]):
                problems.append(f"{where}: FILL needs a ___ and an answer: {line[:60]}")
        if line.startswith("Q:"):
            if waiting:
                problems.append(f"{where}: a question has no answer")
            waiting = True
        elif line.startswith("A:"):
            waiting = False
        if m := re.match(r"^(FIG|COVER):\s*([\w.-]+)", line):
            if not (IMG / m.group(2)).exists():
                problems.append(f"{where}: picture {m.group(2)} is missing")
    if waiting:
        problems.append(f"{where}: the last question has no answer")
    if quiz + sum(l.startswith("Q:") for l in lines) < 2:
        problems.append(f"{where}: fewer than 2 quiz questions")
    return problems


def render_all():
    src = (PUBLIC / "index.html").read_text()
    esc = re.search(r"^const esc=.*$", src, re.M).group(0)
    box = re.search(r"^const boxKind=.*$", src, re.M).group(0)
    start = src.index("function bookHTML(lines")
    fn = src[start:src.index("\n}\n", start) + 3]
    books = {f"{f.parent.name}/{f.stem}": f.read_text() for f in sorted(BOOKS.glob("*/*.txt"))}
    js = f"""{esc}
{box}
{fn}
const books={json.dumps(books, ensure_ascii=False)};const out=[];let n=0,figs=0;
for(const [key,t] of Object.entries(books)){{
  const k=key.split("/")[1];const chs={{}};let c=null;
  for(const line of t.split(/\\r?\\n/)){{const m=line.match(/^@@\\s*(\\d+)\\s*$/);if(m){{c=+m[1];chs[c]=[];continue}}if(c!==null)chs[c].push(line)}}
  for(const [c,ls] of Object.entries(chs)){{n++;
    try{{const h=bookHTML(ls,k);figs+=(h.match(/<figure/g)||[]).length;if(/undefined|NaN/.test(h))out.push(key+" "+c+": shows 'undefined'")}}
    catch(e){{out.push(key+" "+c+": "+e)}}
  }}
}}
out.push("rendered "+n+" chapters, "+figs+" pictures");out.join("\\n");
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js)
    res = subprocess.run(["osascript", "-l", "JavaScript", f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    return (res.stdout or res.stderr).strip()


def main():
    problems, total = [], 0
    for (grade, subject), titles in chapter_titles().items():
        path = BOOKS / grade / f"{subject}.txt"
        if not path.exists():
            problems.append(f"{grade}/{subject}: book file missing")
            continue
        chs = chapters(path)
        for n in range(1, len(titles) + 1):
            if n not in chs:
                problems.append(f"{grade}/{subject} {n}: chapter missing")
                continue
            total += 1
            problems += check_chapter(f"{grade}/{subject} {n}", chs[n])
    print("\n".join(problems) or f"{total} chapters checked: no problems")
    if "--render" in sys.argv:
        print(render_all())
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
