"""Builds assets/header.svg: a night sea with a pixel-art surfer riding a tall wave.

Usage:  python scripts/build_header.py

The surfer is read from a GIF, packed into one sprite strip and embedded in the
SVG, so the header is a single self-contained file that GitHub can show in a
README. Everything that moves is plain CSS inside the SVG.

The camera follows the surfer, so the wave under the board stays put while the
hills, the city and the ships slide past to the left.
"""
import base64
import io
import math
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "header.svg"

# The loop shown on the wave. Swap the file or add entries here later.
SURFER_GIF = ROOT / "assets" / "Chibi Furina Surfing Loop.gif"
SURFER_HEIGHT = 130   # drawn height in header units
SURFER_SPEED = 1.35   # 1 plays the GIF at its own frame rate
SURFER_X = 250        # where the board touches the wave

W, H = 846, 290
HORIZON = 118

# Colours. The scene has its own night sky, so it looks the same on any theme.
SKY_TOP, SKY_LOW = "#070d1a", "#14294a"
SEA_TOP, SEA_LOW = "#10233f", "#081326"
LAND = "#0c1830"
HULL, CLOTH = "#0d1a2e", "#1b2d49"
LINE = "#8b9bb4"
ACCENT = "#5aa9e6"
FOAM = "#b5d9ff"
WARM = "#f2c14e"

# The wave she rides: a tall, smooth swell whose peak sits behind her.
PEAK_X, WAVE_HEIGHT, WAVE_FOOT = 100, 128, 250
BACK_WIDTH, FACE_WIDTH = 120, 230


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


# --- water -----------------------------------------------------------------

def swell_y(x):
    """Height of the big wave's surface at x."""
    width = BACK_WIDTH if x < PEAK_X else FACE_WIDTH
    return WAVE_FOOT - WAVE_HEIGHT * math.exp(-((x - PEAK_X) / width) ** 2)


def swell_slope(x):
    width = BACK_WIDTH if x < PEAK_X else FACE_WIDTH
    return WAVE_HEIGHT * math.exp(-((x - PEAK_X) / width) ** 2) * 2 * (x - PEAK_X) / width ** 2


def swell_line(drop=0.0, start=-30, end=660):
    """The wave's outline, or a line following it `drop` units lower."""
    pts = [(x, swell_y(x) + drop) for x in range(start, end + 1, 6)]
    return "M" + "L".join(f"{x} {y:.1f}" for x, y in pts)


def ripple_line(y, amp, period):
    """A low sine-like line, long enough to scroll one period to the right."""
    d = f"M{-2 * period:g} {y}q{period / 4:g} {-2 * amp} {period / 2:g} 0"
    x = -2 * period + period / 2
    while x < W + period:
        d += f"t{period / 2:g} 0"
        x += period / 2
    return d


# --- scenery ---------------------------------------------------------------

def hills(rng):
    """One screen-wide strip of far hills that starts and ends on the horizon."""
    pts, x = [(0, HORIZON)], 0
    while x < W - 90:
        x += rng.randint(45, 95)
        pts.append((x, HORIZON - rng.randint(8, 34)))
    pts.append((W, HORIZON))
    return "M" + "L".join(f"{x} {y}" for x, y in pts) + "Z"


def skyline(rng):
    """One screen-wide strip of city: roofs, towers, domes and lit windows."""
    d, lights, x = [f"M0 {HORIZON}"], [], 0
    while x < W:
        kind = rng.choices(["house", "tower", "dome", "hall", "gap"], [50, 16, 8, 14, 12])[0]
        w, h = {
            "house": (rng.randint(10, 20), rng.randint(9, 22)),
            "tower": (rng.randint(6, 9), rng.randint(26, 44)),
            "dome": (rng.randint(22, 30), rng.randint(13, 19)),
            "hall": (rng.randint(24, 38), rng.randint(11, 17)),
            "gap": (rng.randint(6, 16), 0),
        }[kind]
        if x + w > W - 8:
            w = W - x
        d.append(f"V{HORIZON - h}")
        if kind == "house" and rng.random() < 0.7:
            r = rng.randint(4, 7)
            d.append(f"l{w / 2:g} {-r}l{w / 2:g} {r}")
        elif kind == "tower":
            s = rng.randint(8, 13)
            d.append(f"l{w / 2:g} {-s}l{w / 2:g} {s}")
        elif kind == "dome":
            d.append(f"h3a{(w - 6) / 2:g} {(w - 6) / 2:g} 0 0 1 {w - 6} 0h3")
        else:
            d.append(f"h{w}")
        if h > 8 and rng.random() < 0.65:
            for _ in range(rng.randint(1, 3)):
                lx = x + rng.uniform(2, max(2.5, w - 4))
                ly = HORIZON - rng.uniform(3, h - 3)
                lights.append(f'<rect x="{lx:.1f}" y="{ly:.1f}" width="1.6" height="2.2"/>')
        x += w
    d.append(f"V{HORIZON}H0Z")
    return "".join(d), "".join(lights)


def sail(mast, top, bottom, w_top, w_bottom):
    mid = (top + bottom) / 2
    a, b = w_top / 2, w_bottom / 2
    return (f"M{mast - a:g} {top:g}H{mast + a:g}Q{mast + b + 2:g} {mid:g} {mast + b:g} {bottom:g}"
            f"Q{mast:g} {bottom + 3:g} {mast - b:g} {bottom:g}Q{mast - b - 2:g} {mid:g} {mast - a:g} {top:g}Z")


def tall_ship():
    """A three-masted ship, bow to the right, waterline on y=0."""
    deck = -16
    cloth = []
    for mast, f in ((-24, 0.85), (4, 1.0), (30, 0.82)):
        for top, bottom, wt, wb in ((-84, -70, 16, 19), (-67, -49, 21, 25), (-46, -25, 26, 30)):
            cloth.append(sail(mast, deck + (top - deck) * f, deck + (bottom - deck) * f, wt * f, wb * f))
    cloth.append("M-26 -50L-48 -40L-46 -22L-26 -24Z")   # spanker at the stern
    cloth.append("M32 -68L74 -27L36 -30Z")              # outer jib
    cloth.append("M32 -50L60 -24L35 -27Z")              # inner jib
    ports = "".join(f'<circle cx="{x}" cy="-9" r="1.3"/>' for x in (-34, -22, -10, 2, 14, 26))
    return f"""<path d="M-24 {deck}V-74M4 {deck}V-92M30 {deck}V-70M54 -18L76 -27M-51 -24V-31" stroke="{LINE}" stroke-width="1.1"/>
        <path d="{''.join(cloth)}" fill="{CLOTH}" stroke="{LINE}" stroke-width="1"/>
        <path d="M4 -92l-10 3 10 3" stroke="{ACCENT}" stroke-width="1.1"/>
        <path d="M-52 -24L-47 -2Q-45 0 -40 0H36Q46 -3 56 -19L42 {deck}H-38L-40 -24Z" fill="{HULL}" stroke="{LINE}" stroke-width="1.1"/>
        <g fill="{WARM}">{ports}<rect x="-47.500" y="-20" width="3" height="3"/><circle cx="-51" cy="-32" r="1.8"/><circle cx="-51" cy="-32" r="5" opacity=".25"/></g>"""


def ship(waterline, scale, secs, delay):
    """A ship drifting left across the scene, with its shadow and reflection."""
    body = tall_ship()
    streaks = "".join(
        f'<path class="shimmer" style="animation-delay:{-i * 0.7}s" d="M{-4 - w / 2:g} {y}h{w}"/>'
        for i, (y, w) in enumerate(((5, 54), (10, 38), (16, 22))))
    return f"""<g transform="translate(0 {waterline})"><g class="pass" style="animation-duration:{secs}s;animation-delay:{delay}s"><g transform="scale({scale})">
        <ellipse cx="2" cy="2" rx="58" ry="3.5" fill="#040a14" opacity=".55"/>
        <g transform="scale(1 -.5)" opacity=".2"><g class="rock">{body}</g></g>
        <g stroke="{WARM}" stroke-width="1.3" opacity=".5">{streaks}</g>
        <g class="rock">{body}</g>
      </g></g></g>"""


def build():
    b64, fw, fh, n, loop_secs = load_strip(SURFER_GIF)
    rng = random.Random(7)
    sw = SURFER_HEIGHT * fw / fh
    ride_y = swell_y(SURFER_X)
    ride_angle = math.degrees(math.atan(swell_slope(SURFER_X))) * 0.7
    peak_y = WAVE_FOOT - WAVE_HEIGHT

    hills_d = hills(rng)
    city_d, city_lights = skyline(rng)
    stars = "".join(
        f'<circle class="star" cx="{rng.randint(10, W - 10)}" cy="{rng.randint(8, HORIZON - 34)}" r="{rng.choice((0.8, 1, 1.2, 1.5))}"/>'
        for _ in range(26))
    face_lines = "".join(
        f'<path class="flow" style="animation-delay:{-k * 0.23:.2f}s" d="{swell_line(drop=k * 15 + k * k)}" stroke-opacity="{0.5 - k * 0.07:.2f}"/>'
        for k in range(1, 6))
    mist = "".join(
        f'<circle class="mist" style="animation-delay:{-i * 0.28:.2f}s" cx="{PEAK_X - 14 + i * 9}" cy="{peak_y + 1 + (i % 2) * 2}" r="{1.6 - (i % 3) * 0.3:.1f}"/>'
        for i in range(6))
    moon_x = 690
    moon_path = "".join(
        f'<path class="shimmer" style="animation-delay:{-i * 0.5}s" d="M{moon_x - w / 2:g} {y}h{w}"/>'
        for i, (y, w) in enumerate(((126, 62), (135, 48), (146, 36), (159, 24), (174, 13))))

    def city():
        tile = (f'<path d="{city_d}" fill="{LAND}" stroke="{LINE}" stroke-opacity=".75" stroke-width="1"/>'
                f'<g fill="{WARM}">{city_lights}</g>')
        return f'<g class="city">{tile}<g transform="translate({W})">{tile}</g></g>'

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <defs>
    <clipPath id="panel"><rect width="{W}" height="{H}" rx="12"/></clipPath>
    <linearGradient id="sky" x1="0" x2="0" y1="0" y2="{HORIZON}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{SKY_TOP}"/><stop offset="1" stop-color="{SKY_LOW}"/>
    </linearGradient>
    <linearGradient id="sea" x1="0" x2="0" y1="{HORIZON}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{SEA_TOP}"/><stop offset="1" stop-color="{SEA_LOW}"/>
    </linearGradient>
    <linearGradient id="face" x1="0" x2="0" y1="{peak_y}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#2f6aa6"/><stop offset=".55" stop-color="#173a66"/><stop offset="1" stop-color="#0b1c36"/>
    </linearGradient>
    <linearGradient id="tail" x1="430" x2="650" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <mask id="fade-tail" maskUnits="userSpaceOnUse" x="-40" y="0" width="{W + 80}" height="{H + 20}"><rect x="-40" width="{W + 80}" height="{H + 20}" fill="url(#tail)"/></mask>
    <radialGradient id="glow"><stop offset="0" stop-color="#cfe3ff" stop-opacity=".32"/><stop offset="1" stop-color="#cfe3ff" stop-opacity="0"/></radialGradient>
    <clipPath id="in-swell"><path d="{swell_line()}V{H + 10}H-30Z"/></clipPath>
  </defs>
  <style>
    .star {{ animation: twinkle 5s ease-in-out infinite alternate; }}
    .star:nth-child(2n) {{ animation-delay: -2s; }}
    .star:nth-child(3n) {{ animation-delay: -3.5s; }}
    .hills {{ animation: scroll 150s linear infinite; }}
    .city {{ animation: scroll 60s linear infinite; }}
    .pass {{ animation: pass linear infinite; }}
    .rock {{ animation: rock 2.6s ease-in-out infinite alternate; }}
    .shimmer {{ animation: shimmer 1.8s ease-in-out infinite alternate; }}
    .ripple {{ animation: drift 5s linear infinite; }}
    .ripple.slow {{ animation-duration: 8s; }}
    .chop {{ animation: chop 3.8s linear infinite; }}
    .chop.near {{ animation-duration: 2.7s; }}
    .heave {{ animation: heave 3.2s ease-in-out infinite alternate; }}
    .flow {{ animation: flow 1.15s linear infinite; }}
    .mist {{ animation: mist 1.7s linear infinite; }}
    .bob {{ animation: bob .9s ease-in-out infinite alternate; }}
    .tilt {{ animation: tilt 1.3s ease-in-out infinite alternate; }}
    .strip {{ animation: frames {loop_secs:.3f}s steps({n}) infinite; image-rendering: pixelated; }}
    .spray {{ animation: spray .7s linear infinite; }}
    .spray.b {{ animation-delay: -.25s; }}
    .spray.c {{ animation-delay: -.48s; }}
    @keyframes twinkle {{ from {{ opacity: 1; }} to {{ opacity: .3; }} }}
    @keyframes scroll {{ to {{ transform: translateX(-{W}px); }} }}
    @keyframes pass {{ from {{ transform: translateX({W + 130}px); }} to {{ transform: translateX(-130px); }} }}
    @keyframes rock {{ from {{ transform: rotate(-2.5deg); }} to {{ transform: rotate(2.5deg); }} }}
    @keyframes shimmer {{ from {{ opacity: 1; transform: translateX(-2px); }} to {{ opacity: .35; transform: translateX(2px); }} }}
    @keyframes drift {{ to {{ stroke-dashoffset: -240; }} }}
    @keyframes chop {{ from {{ transform: translateX(-141px); }} to {{ transform: translateX(0); }} }}
    @keyframes heave {{ from {{ transform: translateY(-3px); }} to {{ transform: translateY(3px); }} }}
    @keyframes flow {{ to {{ stroke-dashoffset: 110; }} }}
    @keyframes mist {{ from {{ transform: translate(0, 0); opacity: .9; }} to {{ transform: translate(-34px, -13px); opacity: 0; }} }}
    @keyframes bob {{ from {{ transform: translateY(-2px); }} to {{ transform: translateY(2px); }} }}
    @keyframes tilt {{ from {{ transform: rotate(-2.5deg); }} to {{ transform: rotate(2.5deg); }} }}
    @keyframes frames {{ to {{ transform: translateX(-{fw * n}px); }} }}
    @keyframes spray {{ from {{ transform: translateX(0); opacity: .9; }} to {{ transform: translateX(-60px); opacity: 0; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>

  <g clip-path="url(#panel)">
    <rect width="{W}" height="{H}" fill="url(#sky)"/>
    <g fill="#c9d6ea">{stars}</g>
    <circle cx="{moon_x}" cy="56" r="62" fill="url(#glow)"/>
    <circle cx="{moon_x}" cy="56" r="25" fill="#dbe9ff" fill-opacity=".14" stroke="{FOAM}" stroke-width="1.5"/>
    <path d="M{moon_x - 12} 41a19 19 0 0 0 3 28" stroke="{FOAM}" stroke-opacity=".5" stroke-width="1.3"/>

    <g class="hills" fill="{LAND}" stroke="{LINE}" stroke-opacity=".4" stroke-width="1">
      <path d="{hills_d}"/><path d="{hills_d}" transform="translate({W})"/>
    </g>

    <rect y="{HORIZON}" width="{W}" height="{H - HORIZON}" fill="url(#sea)"/>
    <g transform="translate(0 {HORIZON}) scale(1 -.45) translate(0 {-HORIZON})" opacity=".28">{city()}</g>
    {city()}
    <path d="M0 {HORIZON}H{W}" stroke="{LINE}" stroke-opacity=".7" stroke-width="1"/>

    <g stroke="{FOAM}" stroke-width="1.6" stroke-opacity=".8">{moon_path}</g>

    <g stroke="{LINE}" stroke-width="1.1" stroke-opacity=".4">
      <path class="ripple slow" d="M0 131H{W}" stroke-dasharray="40 200"/>
      <path class="ripple slow" d="M0 146H{W}" stroke-dasharray="56 184" stroke-dashoffset="120"/>
      <path class="ripple" d="M0 164H{W}" stroke-dasharray="70 170" stroke-dashoffset="60"/>
      <path class="ripple" d="M0 186H{W}" stroke-dasharray="84 156" stroke-dashoffset="150"/>
    </g>

    {ship(141, 0.62, 120, -62)}
    {ship(204, 1.45, 54, -17)}

    <path class="chop" d="{ripple_line(222, 3.5, 141)}" stroke="{LINE}" stroke-opacity=".55" stroke-width="1.2"/>
    <path class="chop near" d="{ripple_line(WAVE_FOOT, 5, 141)}" stroke="{ACCENT}" stroke-width="1.6"/>

    <g class="heave">
      <g mask="url(#fade-tail)">
        <path d="{swell_line()}V{H + 10}H-30Z" fill="url(#face)"/>
        <g clip-path="url(#in-swell)" stroke="{FOAM}" stroke-width="1.3" stroke-dasharray="46 64">{face_lines}</g>
        <path d="{swell_line()}" stroke="{FOAM}" stroke-width="2"/>
      </g>
      <g fill="{FOAM}">{mist}</g>

      <g transform="translate({SURFER_X} {ride_y:.1f}) rotate({ride_angle:.1f})">
        <ellipse cx="-8" cy="5" rx="36" ry="4" fill="#040a14" opacity=".5"/>
        <g class="bob"><g class="tilt">
          <g stroke="{FOAM}" stroke-width="1.6">
            <path class="spray" d="M{-sw / 2 + 12:g} -3h-16"/>
            <path class="spray b" d="M{-sw / 2 + 6:g} -10h-11"/>
            <path class="spray c" d="M{-sw / 2 + 16:g} 2h-20"/>
          </g>
          <svg x="{-sw / 2:g}" y="{4 - SURFER_HEIGHT}" width="{sw:g}" height="{SURFER_HEIGHT}" viewBox="0 0 {fw} {fh}">
            <image class="strip" width="{fw * n}" height="{fh}" href="data:image/png;base64,{b64}"/>
          </svg>
        </g></g>
      </g>
    </g>
  </g>
</svg>
"""
    OUT.write_text(svg, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size / 1024:.0f} KB  ({n} frames, {fw}x{fh})")


if __name__ == "__main__":
    build()
