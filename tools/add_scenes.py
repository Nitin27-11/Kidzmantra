"""Put the chapter scenes and character talk from tools/scenes/ into the books.

Each file tools/scenes/<grade>-<subject>.txt holds lines like:

    3 | 🧲 🧭 📎 | Let's explore magnets!        chapter 3's opening scene
    3.2 riya-wow | Why does the magnet ...       a speech bubble just before the
                                                  chapter's 2nd "##" heading
                                                  (a number past the last heading
                                                  puts it at the end)

Running it again replaces the SCENE and SAY lines it put in before, so the
scene files are the place to edit them. Chapters drawn by hand with a COVER
picture are left alone.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BOOKS = ROOT.parent / "public" / "books"
SCENES = ROOT / "scenes"
SAY = re.compile(r"^(riya|aarav|buddy)-(happy|wow|think)$")


def read_scenes(path):
    scenes, says = {}, {}
    for no, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        where = f"{path.name}:{no}"
        if m := re.match(r"^(\d+)\s*\|\s*([^|]+?)\s*\|\s*(.+)$", line):
            props = m.group(2).split()
            if len(props) != 3:
                sys.exit(f"{where}: a scene needs 3 pictures")
            scenes[int(m.group(1))] = f"SCENE: {' '.join(props)} | {m.group(3)}"
        elif m := re.match(r"^(\d+)\.(\d+)\s+(\S+)\s*\|\s*(.+)$", line):
            if not SAY.match(m.group(3)):
                sys.exit(f"{where}: unknown speaker {m.group(3)}")
            says.setdefault(int(m.group(1)), []).append((int(m.group(2)), f"SAY: {m.group(3)} | {m.group(4)}"))
        else:
            sys.exit(f"{where}: can't read this line")
    return scenes, says


def split_chapters(text):
    head, chapters, cur = [], {}, None
    for line in text.splitlines():
        if m := re.match(r"^@@\s*(\d+)\s*$", line):
            cur = int(m.group(1))
            chapters[cur] = [line]
        elif cur is None:
            head.append(line)
        else:
            chapters[cur].append(line)
    return head, chapters


def place(lines, scene, says):
    if any(l.startswith("COVER:") for l in lines):
        return lines
    lines = [l for l in lines if not l.startswith(("SCENE:", "SAY:"))]
    out, heading = [lines[0]], 0
    if scene:
        out += [scene, ""]
    body = lines[1:]
    while body and not body[0].strip():
        body.pop(0)
    for line in body:
        if line.startswith("## "):
            heading += 1
            mine = [s for k, s in says if k == heading]
            if mine:
                while len(out) > 1 and not out[-1].strip():
                    out.pop()
                out += [""] + mine + [""]
        out.append(line)
    tail = [s for k, s in says if k > heading]
    if tail:
        while out and not out[-1].strip():
            out.pop()
        out += [""] + tail
    return out + [""]


def main():
    total = 0
    for path in sorted(SCENES.glob("*.txt")):
        grade, subject = path.stem.rsplit("-", 1)
        book = BOOKS / grade / f"{subject}.txt"
        scenes, says = read_scenes(path)
        head, chapters = split_chapters(book.read_text())
        for n in set(scenes) | set(says):
            if n not in chapters:
                sys.exit(f"{path.name}: {book.relative_to(BOOKS)} has no chapter {n}")
        for n in chapters:
            if n in scenes or n in says:
                chapters[n] = place(chapters[n], scenes.get(n), says.get(n, []))
                total += 1
        text = "\n".join(head + [l for n in sorted(chapters) for l in chapters[n]])
        book.write_text(re.sub(r"\n{3,}", "\n\n", text).rstrip("\n") + "\n")
    print(f"scenes and talk placed in {total} chapters")


if __name__ == "__main__":
    main()
