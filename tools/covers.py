"""Chapter cover illustrations featuring Riya, Aarav and Buddy.

Each cover is a function returning the props for one chapter; build() frames
them with the characters, a title band and a speech bubble. Run this file to
(re)build every cover into public/books/img/.
"""

from characters import IMG, draw_aarav, draw_buddy, draw_riya

W, H = 760, 330


def frame(chapter_label, title, bubble, props, moods=("wow", "happy", "happy"), sky="#e8f4ff"):
    riya, aarav, buddy = moods
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="{sky}"/>
  <circle cx="680" cy="70" r="120" fill="#fff" opacity=".5"/><circle cx="90" cy="250" r="140" fill="#fff" opacity=".35"/>
  <rect y="286" width="{W}" height="44" fill="#f3e3c3"/>
  <rect x="0" y="0" width="{W}" height="44" fill="#1e2a3a"/>
  <text x="24" y="29" font-size="18" fill="#ffd166" font-weight="bold">{chapter_label}</text>
  <text x="{W - 24}" y="29" font-size="18" fill="#fff" font-weight="bold" text-anchor="end">{title}</text>
  {draw_riya(200, 200, 1.1, riya)}
  {draw_aarav(410, 200, 1.1, aarav)}
  {draw_buddy(640, 200, 1.1, buddy)}
  {props}
  <g>
    <rect x="470" y="58" width="250" height="46" rx="16" fill="#fff" stroke="#2bb3a3" stroke-width="3"/>
    <path d="M610 104 l14 18 l2 -18 z" fill="#fff" stroke="#2bb3a3" stroke-width="3" stroke-linejoin="round"/>
    <rect x="606" y="100" width="22" height="6" fill="#fff"/>
    <text x="595" y="88" font-size="17" text-anchor="middle" fill="#1e2a3a" font-weight="bold">{bubble}</text>
  </g>
</svg>
'''


def c6_sci_4():
    """Exploring Magnets: Riya lifts paper clips with a horseshoe magnet; Aarav holds a compass."""
    clips = "".join(
        f'<rect x="{214 + i * 4}" y="{244 + i * 16}" width="10" height="18" rx="5" fill="none" stroke="#666" stroke-width="2.5"/>'
        for i in range(3))
    props = f'''
  <g transform="translate(62 28)">
  <g transform="translate(200 200) rotate(180) translate(-200 -200)">
    <path d="M178 150 v34 a22 22 0 0 0 44 0 v-34 h-12 v34 a10 10 0 0 1 -20 0 v-34 z" fill="#888"/>
    <rect x="178" y="150" width="12" height="12" fill="#e04848"/><rect x="210" y="150" width="12" height="12" fill="#3a6fd8"/>
  </g>
  {clips}
  </g>
  <g transform="translate(492 262)">
    <circle r="34" fill="#f6f1e4" stroke="#333" stroke-width="4"/><circle r="27" fill="#fff"/>
    <text y="-14" font-size="11" font-weight="bold" text-anchor="middle" fill="#e04848">N</text>
    <text y="22" font-size="11" font-weight="bold" text-anchor="middle" fill="#333">S</text>
    <polygon points="0,-20 6,0 -6,0" fill="#e04848"/><polygon points="0,20 6,0 -6,0" fill="#3a6fd8"/><circle r="3" fill="#333"/>
  </g>
  <g transform="translate(24 140)">
    <rect width="70" height="142" rx="8" fill="#dfe6ee" stroke="#9aa7b4" stroke-width="2"/><line x1="0" y1="52" x2="70" y2="52" stroke="#9aa7b4" stroke-width="2"/>
    <rect x="56" y="18" width="5" height="24" rx="2" fill="#9aa7b4"/><rect x="56" y="64" width="5" height="30" rx="2" fill="#9aa7b4"/>
    <circle cx="20" cy="78" r="7" fill="#ff6b6b"/><rect x="28" y="96" width="14" height="10" rx="2" fill="#ffd166"/><circle cx="22" cy="118" r="6" fill="#4cc48e"/>
  </g>'''
    return frame("Class 6 · Science · Chapter 4", "Exploring Magnets", "Let's explore magnets!", props)


COVERS = {"cover-c6-sci-4.svg": c6_sci_4}


def build():
    for name, make in COVERS.items():
        (IMG / name).write_text(make())


if __name__ == "__main__":
    build()
    print("covers written:", ", ".join(COVERS))
