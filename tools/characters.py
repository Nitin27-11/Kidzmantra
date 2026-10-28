"""Draw the Kidzmantra characters (Riya, Aarav, Buddy) as SVG.

Each draw_* function returns an SVG <g> group for a character bust centred on
(x, y) with the given scale, so the same character can be reused in portraits
and in chapter cover scenes. Run this file to (re)build the portrait files in
public/books/img/.
"""

from pathlib import Path

IMG = Path(__file__).resolve().parent.parent / "public" / "books" / "img"

MOODS = ("happy", "wow", "think")


def _mouth(mood, cx, cy):
    if mood == "wow":
        return f'<ellipse cx="{cx}" cy="{cy + 2}" rx="6" ry="8" fill="#7a2e2e"/>'
    if mood == "think":
        return f'<path d="M{cx - 8} {cy + 3} q8 -4 16 0" stroke="#5a2a1a" stroke-width="3" fill="none" stroke-linecap="round"/>'
    return f'<path d="M{cx - 11} {cy - 2} q11 13 22 0" fill="#fff" stroke="#5a2a1a" stroke-width="3" stroke-linejoin="round"/>'


def _eyes(mood, cx, cy, gap=14):
    left, right = cx - gap, cx + gap
    if mood == "think":
        eyes = (f'<circle cx="{left}" cy="{cy}" r="4.5" fill="#2b1a12"/><circle cx="{right}" cy="{cy}" r="4.5" fill="#2b1a12"/>'
                f'<path d="M{left - 6} {cy - 10} h12 M{right - 6} {cy - 12} q6 -6 12 -2" stroke="#2b1a12" stroke-width="3" fill="none" stroke-linecap="round"/>')
    else:
        r = 6 if mood == "wow" else 5
        eyes = (f'<circle cx="{left}" cy="{cy}" r="{r}" fill="#2b1a12"/><circle cx="{right}" cy="{cy}" r="{r}" fill="#2b1a12"/>'
                f'<circle cx="{left + 2}" cy="{cy - 2}" r="1.8" fill="#fff"/><circle cx="{right + 2}" cy="{cy - 2}" r="1.8" fill="#fff"/>')
    return eyes


def draw_riya(x=80, y=80, s=1.0, mood="happy"):
    """Riya: curious girl with two ponytails and a yellow kurta top."""
    return f'''<g transform="translate({x - 80 * s} {y - 80 * s}) scale({s})">
  <circle cx="34" cy="62" r="17" fill="#2e1a12"/><circle cx="126" cy="62" r="17" fill="#2e1a12"/>
  <circle cx="44" cy="54" r="6" fill="#e0457b"/><circle cx="116" cy="54" r="6" fill="#e0457b"/>
  <path d="M38 160 q0 -38 42 -38 q42 0 42 38 z" fill="#f5b82e"/>
  <path d="M68 124 l12 14 l12 -14" fill="none" stroke="#c98a12" stroke-width="3"/>
  <rect x="72" y="108" width="16" height="16" fill="#c68b59"/>
  <circle cx="80" cy="80" r="38" fill="#c68b59"/>
  <path d="M42 78 q-2 -40 38 -42 q40 2 38 42 q-10 -22 -38 -24 q-28 2 -38 24 z" fill="#2e1a12"/>
  {_eyes(mood, 80, 84)}
  <circle cx="58" cy="96" r="5" fill="#e98a7a" opacity=".6"/><circle cx="102" cy="96" r="5" fill="#e98a7a" opacity=".6"/>
  {_mouth(mood, 80, 101)}
</g>'''


def draw_aarav(x=80, y=80, s=1.0, mood="happy"):
    """Aarav: playful boy with spiky hair, round glasses and a blue T-shirt."""
    return f'''<g transform="translate({x - 80 * s} {y - 80 * s}) scale({s})">
  <path d="M36 160 q0 -38 44 -38 q44 0 44 38 z" fill="#3a6fd8"/>
  <path d="M66 124 q14 12 28 0" fill="none" stroke="#244c9e" stroke-width="3"/>
  <rect x="72" y="108" width="16" height="16" fill="#b57a4c"/>
  <circle cx="42" cy="84" r="7" fill="#b57a4c"/><circle cx="118" cy="84" r="7" fill="#b57a4c"/>
  <circle cx="80" cy="82" r="38" fill="#b57a4c"/>
  <path d="M42 76 l4 -22 l10 8 l6 -18 l10 12 l8 -16 l8 14 l10 -10 l4 16 l12 -4 l-2 20 q-18 -16 -70 0 z" fill="#1d1410"/>
  {_eyes(mood, 80, 86, gap=15)}
  <circle cx="65" cy="86" r="11" fill="none" stroke="#2b2b2b" stroke-width="2.5"/>
  <circle cx="95" cy="86" r="11" fill="none" stroke="#2b2b2b" stroke-width="2.5"/>
  <path d="M76 86 h8" stroke="#2b2b2b" stroke-width="2.5"/>
  {_mouth(mood, 80, 104)}
</g>'''


def draw_buddy(x=80, y=80, s=1.0, mood="happy"):
    """Buddy: the friendly robot teacher (Mantra Buddy)."""
    face = {"happy": '<path d="M68 96 q12 10 24 0" stroke="#5ff0e0" stroke-width="4" fill="none" stroke-linecap="round"/>',
            "wow": '<circle cx="80" cy="98" r="6" fill="none" stroke="#5ff0e0" stroke-width="4"/>',
            "think": '<path d="M70 98 h20" stroke="#5ff0e0" stroke-width="4" stroke-linecap="round"/>'}[mood]
    eyes = ('<rect x="62" y="74" width="8" height="12" rx="4" fill="#5ff0e0"/><rect x="90" y="74" width="8" height="12" rx="4" fill="#5ff0e0"/>'
            if mood != "happy" else
            '<path d="M60 82 q6 -8 12 0 M88 82 q6 -8 12 0" stroke="#5ff0e0" stroke-width="4" fill="none" stroke-linecap="round"/>')
    return f'''<g transform="translate({x - 80 * s} {y - 80 * s}) scale({s})">
  <path d="M40 160 q0 -34 40 -34 q40 0 40 34 z" fill="#2bb3a3"/>
  <circle cx="80" cy="146" r="7" fill="#ffd166"/>
  <line x1="80" y1="40" x2="80" y2="24" stroke="#2bb3a3" stroke-width="4"/><circle cx="80" cy="20" r="7" fill="#ff6b6b"/>
  <rect x="34" y="72" width="10" height="24" rx="4" fill="#1f8f83"/><rect x="116" y="72" width="10" height="24" rx="4" fill="#1f8f83"/>
  <rect x="42" y="40" width="76" height="80" rx="22" fill="#2bb3a3"/>
  <rect x="52" y="56" width="56" height="54" rx="14" fill="#1e2a3a"/>
  {eyes}
  {face}
</g>'''


DRAW = {"riya": draw_riya, "aarav": draw_aarav, "buddy": draw_buddy}
BG = {"riya": "#ffe9a8", "aarav": "#cfe6ff", "buddy": "#d8f5e7"}


def portrait(name, mood="happy"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160" width="160" height="160">'
            f'<clipPath id="c"><circle cx="80" cy="80" r="80"/></clipPath>'
            f'<g clip-path="url(#c)"><rect width="160" height="160" fill="{BG[name]}"/>{DRAW[name](mood=mood)}</g></svg>\n')


def figure(name, mood="happy"):
    """The character on a transparent background, for chapter scenes."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="14 8 132 152" width="132" height="152">'
            f'{DRAW[name](mood=mood)}</svg>\n')


def write_portraits():
    IMG.mkdir(parents=True, exist_ok=True)
    for name in DRAW:
        for mood in MOODS:
            (IMG / f"char-{name}-{mood}.svg").write_text(portrait(name, mood))
            (IMG / f"char-{name}-{mood}-full.svg").write_text(figure(name, mood))


if __name__ == "__main__":
    write_portraits()
    print("portraits written to", IMG)
