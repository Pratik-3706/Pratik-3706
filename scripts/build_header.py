"""Builds assets/header.svg: a line-art night sea with a pixel-art surfer.

Usage:  python scripts/build_header.py

The surfer is read from a GIF, packed into one sprite strip and embedded in the
SVG, so the header is a single self-contained file that GitHub can show in a
README. Everything that moves is plain CSS inside the SVG.
"""
import base64
import io
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "header.svg"

# The loop shown on the wave. Swap the file or add entries here later.
SURFER_GIF = ROOT / "assets" / "Chibi Furina Surfing Loop.gif"
SURFER_HEIGHT = 128  # drawn height in header units
SURFER_SPEED = 1.35  # 1 plays the GIF at its own frame rate

W, H = 846, 240
ACCENT = "#4a9eda"
MUTED = "#8b949e"

SURF_X = 190  # where the board's centre sits
FRONT_Y, FRONT_AMP, FRONT_PERIOD, FRONT_SECS = 204, 8, 282, 2.7
MID_Y, MID_AMP, MID_PERIOD, MID_SECS = 178, 4, 141, 3.8


def load_strip(path):
    """Returns (base64 png, frame w, frame h, frame count, seconds per loop)."""
    gif = Image.open(path)
    frames, total_ms = [], 0
    for i in range(gif.n_frames):
        gif.seek(i)
        total_ms += gif.info.get("duration", 100)
        frames.append(gif.convert("RGBA"))
    # The GIF moves the board up and down by itself. Pin every frame's lowest
    # pixel to the same line so the board stays on the wave drawn here.
    boxes = [f.getbbox() for f in frames]
    left, right = min(b[0] for b in boxes), max(b[2] for b in boxes)
    fw, fh = right - left, max(b[3] - b[1] for b in boxes)
    strip = Image.new("RGBA", (fw * len(frames), fh), (0, 0, 0, 0))
    for i, (f, b) in enumerate(zip(frames, boxes)):
        strip.paste(f.crop((left, b[3] - fh, right, b[3])), (i * fw, 0))
    buf = io.BytesIO()
    strip.quantize(255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(
        buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), fw, fh, len(frames), total_ms / 1000 / SURFER_SPEED


def wave_path(y, amp, period, crest_x, close_to=None):
    """A sine-like line with a crest at crest_x, long enough to scroll one period.

    The waves travel right, the way the surfer is heading, as a real wave does.
    """
    start = crest_x - period / 4
    while start > -period:
        start -= period
    d = f"M{start:g} {y}q{period / 4:g} {-2 * amp} {period / 2:g} 0"
    x = start + period / 2
    while x < W + period:
        d += f"t{period / 2:g} 0"
        x += period / 2
    if close_to is not None:
        d += f"V{close_to}H{start:g}Z"
    return d


def city(cx, base):
    """A far-off tiered city on the horizon: stepped terraces, towers, a domed spire."""
    def tower(x, foot, top, roof):
        return f"M{x - 3} {foot}V{top}L{x} {roof}L{x + 3} {top}V{foot}"

    d = [
        f"M{cx - 90} {base}V{base - 16}H{cx + 90}V{base}",            # sea wall
        f"M{cx - 64} {base - 16}V{base - 27}H{cx + 64}V{base - 16}",  # middle terrace
        f"M{cx - 36} {base - 27}V{base - 37}H{cx + 36}V{base - 27}",  # upper terrace
        f"M{cx - 7} {base - 37}V{base - 62}M{cx + 7} {base - 37}V{base - 62}",
        f"M{cx - 10} {base - 62}H{cx + 10}M{cx - 9} {base - 62}a9 9 0 0 1 18 0",
        f"M{cx} {base - 71}V{base - 84}",
        tower(cx - 51, base - 27, base - 44, base - 52),
        tower(cx + 51, base - 27, base - 44, base - 52),
        tower(cx - 79, base - 16, base - 30, base - 37),
        tower(cx + 79, base - 16, base - 30, base - 37),
    ]
    for off in (-66, -44, -22, 22, 44, 66):                            # arches in the wall
        d.append(f"M{cx + off - 5} {base}v-6a5 5 0 0 1 10 0v6")
    falls = "".join(f"M{cx + off} {base - 14}V{base - 1}" for off in (-55, 0, 55))
    return "".join(d), falls


SHIP = ("M-22 0h44q-3 9-10 9h-22q-8 0-12-9z"   # hull, bow to the right
        "M0 0v-30"                              # mast
        "M-2-28q-14 10-16 24h16z"               # mainsail
        "M2-26l13 22h-13z"                      # jib
        "M0-30l-6 2 6 2")                       # pennant


def ship(y, scale, secs, delay):
    return (f'<g transform="translate(0 {y})"><g class="sail" style="animation-duration:{secs}s;'
            f'animation-delay:{delay}s"><g transform="scale({scale})">'
            f'<path class="rock" d="{SHIP}"/></g></g></g>')


def build():
    b64, fw, fh, n, loop_secs = load_strip(SURFER_GIF)
    sw = SURFER_HEIGHT * fw / fh
    sx, sy = SURF_X - sw / 2, FRONT_Y - SURFER_HEIGHT + 4
    half = FRONT_SECS / 2
    crest = FRONT_Y - FRONT_AMP

    hills = "M30 128L88 110L120 119L166 101L222 124L260 128M505 128L548 117L588 123L616 128"
    city_d, falls_d = city(385, 128)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <defs>
    <linearGradient id="fade" x1="0" x2="{W}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#fff" stop-opacity="0"/>
      <stop offset=".12" stop-color="#fff"/>
      <stop offset=".88" stop-color="#fff"/>
      <stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <mask id="edges"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>
    <linearGradient id="water" x1="0" x2="0" y1="{crest}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{ACCENT}" stop-opacity=".22"/>
      <stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <style>
    .falls {{ animation: fall 1.2s linear infinite; }}
    .sail {{ animation: sail linear infinite; }}
    .rock {{ animation: rock 2.6s ease-in-out infinite alternate; }}
    .ripple {{ animation: drift 5s linear infinite; }}
    .ripple.slow {{ animation-duration: 8s; }}
    .mid {{ animation: slide-mid {MID_SECS}s linear infinite; }}
    .front {{ animation: slide-front {FRONT_SECS}s linear infinite; }}
    .bob {{ animation: bob {half}s ease-in-out infinite alternate; }}
    .tilt {{ animation: tilt {half}s ease-in-out {-half / 2}s infinite alternate; transform-origin: {SURF_X}px {FRONT_Y}px; }}
    .strip {{ animation: frames {loop_secs}s steps({n}) infinite; image-rendering: pixelated; }}
    .spray {{ animation: spray .7s linear infinite; }}
    .spray.b {{ animation-delay: -.25s; }}
    .spray.c {{ animation-delay: -.48s; }}
    .star {{ animation: twinkle 5s ease-in-out infinite alternate; }}
    .star:nth-child(2n) {{ animation-delay: -2s; }}
    .star:nth-child(3n) {{ animation-delay: -3.5s; }}
    @keyframes fall {{ to {{ stroke-dashoffset: -6; }} }}
    @keyframes sail {{ from {{ transform: translateX({W + 50}px); }} to {{ transform: translateX(-50px); }} }}
    @keyframes rock {{ from {{ transform: rotate(-3deg); }} to {{ transform: rotate(3deg); }} }}
    @keyframes drift {{ to {{ stroke-dashoffset: -240; }} }}
    @keyframes slide-mid {{ from {{ transform: translateX(-{MID_PERIOD}px); }} to {{ transform: translateX(0); }} }}
    @keyframes slide-front {{ from {{ transform: translateX(-{FRONT_PERIOD}px); }} to {{ transform: translateX(0); }} }}
    @keyframes bob {{ from {{ transform: translateY(-{FRONT_AMP}px); }} to {{ transform: translateY({FRONT_AMP}px); }} }}
    @keyframes tilt {{ from {{ transform: rotate(4deg); }} to {{ transform: rotate(-4deg); }} }}
    @keyframes frames {{ to {{ transform: translateX(-{fw * n}px); }} }}
    @keyframes spray {{ from {{ transform: translateX(0); opacity: .8; }} to {{ transform: translateX(-70px); opacity: 0; }} }}
    @keyframes twinkle {{ from {{ opacity: 1; }} to {{ opacity: .35; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>

  <g mask="url(#edges)">
    <g fill="{MUTED}">
      <circle class="star" cx="96" cy="38" r="1.3"/>
      <circle class="star" cx="188" cy="74" r="1"/>
      <circle class="star" cx="262" cy="26" r="1.5"/>
      <circle class="star" cx="351" cy="62" r="1"/>
      <circle class="star" cx="438" cy="30" r="1.2"/>
      <circle class="star" cx="512" cy="80" r="1"/>
      <circle class="star" cx="566" cy="22" r="1.3"/>
      <circle class="star" cx="728" cy="36" r="1"/>
      <circle class="star" cx="772" cy="84" r="1.3"/>
    </g>

    <circle cx="650" cy="70" r="29" stroke="{ACCENT}" stroke-width="1.6"/>
    <path d="M636 53a21 21 0 0 0 4 32" stroke="{ACCENT}" stroke-opacity=".55" stroke-width="1.4"/>

    <path d="{hills}" stroke="{MUTED}" stroke-opacity=".55" stroke-width="1.2"/>
    <path d="{city_d}" stroke="{MUTED}" stroke-opacity=".8" stroke-width="1.1"/>
    <path class="falls" d="{falls_d}" stroke="{ACCENT}" stroke-opacity=".8" stroke-width="1.4" stroke-dasharray="3 3"/>
    <path d="M0 128H{W}" stroke="{MUTED}" stroke-opacity=".9" stroke-width="1.2"/>

    <g stroke="{ACCENT}" stroke-width="1.6">
      <path d="M612 140H688" stroke-opacity=".9"/>
      <path d="M624 151H676" stroke-opacity=".65"/>
      <path d="M635 162H665" stroke-opacity=".4"/>
    </g>

    <g stroke="{MUTED}" stroke-width="1.2" stroke-opacity=".45">
      <path class="ripple slow" d="M0 142H{W}" stroke-dasharray="46 194"/>
      <path class="ripple" d="M0 157H{W}" stroke-dasharray="64 176" stroke-dashoffset="90"/>
    </g>

    <g stroke="{MUTED}" stroke-opacity=".8" stroke-width="1.2">
      {ship(138, .5, 80, -30)}
      {ship(165, .95, 42, -31)}
    </g>

    <path class="mid" d="{wave_path(MID_Y, MID_AMP, MID_PERIOD, 0)}" stroke="{MUTED}" stroke-opacity=".6" stroke-width="1.3"/>

    <path class="front" d="{wave_path(FRONT_Y, FRONT_AMP, FRONT_PERIOD, SURF_X, close_to=H)}" fill="url(#water)"/>
    <path class="front" d="{wave_path(FRONT_Y, FRONT_AMP, FRONT_PERIOD, SURF_X)}" stroke="{ACCENT}" stroke-width="1.8"/>

    <g class="bob">
      <g class="tilt">
        <g stroke="{ACCENT}" stroke-width="1.6">
          <path class="spray" d="M{sx + 10:g} {FRONT_Y - 7}h-16"/>
          <path class="spray b" d="M{sx + 4:g} {FRONT_Y - 14}h-11"/>
          <path class="spray c" d="M{sx + 14:g} {FRONT_Y - 1}h-20"/>
        </g>
        <svg x="{sx:g}" y="{sy:g}" width="{sw:g}" height="{SURFER_HEIGHT}" viewBox="0 0 {fw} {fh}">
          <image class="strip" width="{fw * n}" height="{fh}" href="data:image/png;base64,{b64}"/>
        </svg>
      </g>
    </g>
  </g>
</svg>
"""
    OUT.write_text(svg, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size / 1024:.0f} KB  ({n} frames, {fw}x{fh})")


if __name__ == "__main__":
    build()
