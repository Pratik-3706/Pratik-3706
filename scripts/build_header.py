"""Builds assets/header.svg: a night sea with a pixel-art surfer riding a tall wave.

Usage:  python scripts/build_header.py

The surfer is read from GIF loops, packed into one sprite strip and embedded in
the SVG, so the header is a single self-contained file that GitHub can show in
a README. Everything that moves is plain CSS inside the SVG.

The camera travels with the surfer and her wave, so the wave stays put in the
frame while the coast, the ships and the small chop slide past to the left.
"""
import base64
import io
import math
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUT = ASSETS / "header.svg"

# The loops she plays, in order. Each entry is:
#   (file, times to play, speed, pin)
# pin=True keeps the board glued to the water in every frame; pin=False keeps
# the GIF's own up-and-down movement, which is what a jump needs.
LOOPS = [
    (ASSETS / "Chibi Furina Surfing Loop.gif", 3, 1.35, True),
    (ASSETS / "Chibi Surfer’s Animated Board Grab.gif", 1, 1.2, False),
]
SURFER_HEIGHT = 128   # drawn height of her standing pose, in header units

W, H = 846, 300
WATER = 126           # where the sea meets the coast
CITY_BASE = 116       # top of the quay the city stands on

# Colours. The scene has its own night sky, so it looks the same on any theme.
SKY_TOP, SKY_LOW = "#070d1a", "#14294a"
SEA_TOP, SEA_LOW = "#10233f", "#081326"
LAND, QUAY = "#0c1830", "#1a2a45"
HULL, DECK = "#0d1a2e", "#1b2d49"
LINE = "#8b9bb4"
ACCENT = "#5aa9e6"
FOAM = "#b5d9ff"
WARM = "#f2c14e"

# The wave she rides. It travels right with her: a sharp crest behind her, a
# steep hollow face she runs down, and a trough out in front.
CREST_X, CREST_Y = 170, 94
FACE_LENGTH, TROUGH_Y = 330, 264
FACE_CURVE = 2.3      # above 1 makes the face hollow: steep at the top, flat at the foot
SURFER_AT = 0.43      # how far down the face she sits, 0 = crest, 1 = trough


# --- surfer ----------------------------------------------------------------

def load_sprites(loops):
    """Packs every frame of every loop into one strip.

    Returns (base64 png, cell w, cell h, anchor x, anchor y, timeline, standing h)
    where the anchor is the point of a cell that sits on the water and the
    timeline is a list of (frame index, seconds).
    """
    placed, timeline, standing = [], [], None
    for path, times, speed, pin in loops:
        gif = Image.open(path)
        first = len(placed)
        frames, secs = [], []
        for i in range(gif.n_frames):
            gif.seek(i)
            secs.append(gif.info.get("duration", 100) / 1000 / speed)
            frames.append(gif.convert("RGBA"))
        boxes = [f.getbbox() for f in frames]
        anchor_x = (boxes[0][0] + boxes[0][2]) // 2
        if standing is None:
            standing = boxes[0][3] - boxes[0][1]
        for f, b in zip(frames, boxes):
            foot = b[3] if pin else boxes[0][3]
            placed.append((f.crop(b), b[0] - anchor_x, b[1] - foot))
        for _ in range(times):
            timeline += [(first + i, s) for i, s in enumerate(secs)]

    left = min(dx for _, dx, _ in placed)
    top = min(dy for _, _, dy in placed)
    cw = max(dx + im.width for im, dx, _ in placed) - left
    ch = max(dy + im.height for im, _, dy in placed) - top
    strip = Image.new("RGBA", (cw * len(placed), ch), (0, 0, 0, 0))
    for i, (im, dx, dy) in enumerate(placed):
        strip.paste(im, (i * cw + dx - left, dy - top))
    buf = io.BytesIO()
    strip.quantize(255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(
        buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), cw, ch, -left, -top, timeline, standing


def frame_keyframes(timeline, cw):
    """CSS keyframes that jump the strip to each frame at the right moment."""
    total = sum(s for _, s in timeline)
    out, t = [], 0.0
    for idx, secs in timeline:
        out.append(f"{t / total * 100:.3f}% {{ transform: translateX(-{idx * cw}px); }}")
        t += secs
    out.append(f"100% {{ transform: translateX(-{timeline[0][0] * cw}px); }}")
    return " ".join(out), total


# --- water -----------------------------------------------------------------

def wave_y(x):
    """Height of the big wave's surface at x."""
    if x < CREST_X:                      # the back: a long easy slope
        return CREST_Y + 92 * (1 - math.exp(-((CREST_X - x) / 150) ** 1.6))
    s = (x - CREST_X) / FACE_LENGTH
    if s < 1:                            # the face
        return TROUGH_Y - (TROUGH_Y - CREST_Y) * (1 - s) ** FACE_CURVE
    return TROUGH_Y - 5 * (1 - math.exp(-(x - CREST_X - FACE_LENGTH) / 90))


def wave_slope(x):
    return (wave_y(x + 0.5) - wave_y(x - 0.5))


def wave_line(drop=0.0, start=-30, end=760, step=5):
    """The wave's outline, or a line following it `drop` units lower."""
    pts = [(x, wave_y(x) + drop) for x in range(start, end + 1, step)]
    return "M" + "L".join(f"{x} {y:.1f}" for x, y in pts)


def chop_line(y, amp, period):
    """A low sine-like line, long enough to scroll one period."""
    d = f"M{-period:g} {y}q{period / 4:g} {-2 * amp} {period / 2:g} 0"
    x = -period + period / 2
    while x < W + 2 * period:
        d += f"t{period / 2:g} 0"
        x += period / 2
    return d


# --- scenery ---------------------------------------------------------------

def hills(rng):
    """One screen-wide strip of far hills that starts and ends at the same height."""
    pts, x = [(0, WATER), (0, CITY_BASE - 6)], 0
    while x < W - 90:
        x += rng.randint(45, 95)
        pts.append((x, CITY_BASE - rng.randint(10, 40)))
    pts += [(W, CITY_BASE - 6), (W, WATER)]
    return "M" + "L".join(f"{x} {y}" for x, y in pts) + "Z"


def skyline(rng):
    """One screen-wide strip of city on its quay: roofs, towers, domes, lit windows."""
    base = CITY_BASE
    d, lights, x = [f"M0 {base}"], [], 0
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
        d.append(f"V{base - h}")
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
                ly = base - rng.uniform(3, h - 3)
                lights.append(f'<rect x="{lx:.1f}" y="{ly:.1f}" width="1.6" height="2.2"/>')
        x += w
    d.append(f"V{base}H0Z")

    # The coast itself: a quay wall with street lamps, and a lighthouse on it.
    lamps = "".join(f'<circle cx="{lx}" cy="{base + 2.5}" r="1"/>' for lx in range(14, W, 47))
    lx = 610
    lighthouse = (
        f'<path d="M{lx - 5} {base}L{lx - 3} {base - 34}H{lx + 3}L{lx + 5} {base}Z'
        f'M{lx - 4} {base - 34}V{base - 40}H{lx + 4}V{base - 34}M{lx - 5} {base - 40}L{lx} {base - 45}L{lx + 5} {base - 40}" '
        f'fill="{LAND}" stroke="{LINE}" stroke-opacity=".8" stroke-width="1"/>'
        f'<g class="blink" fill="{WARM}"><circle cx="{lx}" cy="{base - 37}" r="2"/>'
        f'<circle cx="{lx}" cy="{base - 37}" r="8" opacity=".25"/></g>')
    return (
        f'<path d="{"".join(d)}" fill="{LAND}" stroke="{LINE}" stroke-opacity=".75" stroke-width="1"/>'
        f'<g fill="{WARM}">{"".join(lights)}</g>{lighthouse}'
        f'<rect y="{base}" width="{W}" height="{WATER - base}" fill="{QUAY}"/>'
        f'<path d="M0 {base}H{W}" stroke="{LINE}" stroke-opacity=".8" stroke-width="1"/>'
        f'<path d="M0 {base + 6}H{W}" stroke="{LINE}" stroke-opacity=".35" stroke-width="1" stroke-dasharray="3 9"/>'
        f'<g fill="{WARM}">{lamps}</g>')


def cruise_ship():
    """A cruise liner, bow to the right, waterline on y=0. About 160 long."""
    decks = ((-70, 56, -16, -23), (-64, 47, -23, -30), (-56, 38, -30, -37), (-44, 26, -37, -43))
    deck_d = "".join(f"M{x0} {yb}H{x1}L{x1 - 5} {yt}H{x0 + 2}Z" for x0, x1, yb, yt in decks)
    windows = "".join(
        f'<rect x="{x}" y="{yt + 2.2}" width="2.6" height="2.2"/>'
        for x0, x1, yb, yt in decks for x in range(x0 + 5, x1 - 9, 6))
    ports = "".join(f'<circle cx="{x}" cy="-8" r="1.1"/>' for x in range(-66, 62, 8))
    return f"""<path d="M-78 -15L-74 -2Q-73 0 -68 0H60Q69 -4 80 -17Z" fill="{HULL}" stroke="{LINE}" stroke-width="1.1"/>
        <path d="M-76 -6H66" stroke="{ACCENT}" stroke-opacity=".6" stroke-width="1"/>
        <path d="{deck_d}M-38 -43L-36 -57H-24L-21 -43Z" fill="{DECK}" stroke="{LINE}" stroke-width="1"/>
        <path d="M-36.500 -52H-23M12 -43V-56M7 -51H17" stroke="{ACCENT}" stroke-width="1.2"/>
        <circle cx="12" cy="-57.500" r="1.4" fill="{ACCENT}"/>
        <g fill="{WARM}">{windows}{ports}</g>"""


def container_ship():
    """A container ship, bow to the right, waterline on y=0. About 160 long."""
    rng = random.Random(3)
    boxes = []
    for x in range(-40, 58, 12):
        for row in range(rng.randint(2, 4)):
            shade = rng.choice((DECK, "#22385a", "#17324f", "#2a4468"))
            boxes.append(f'<rect x="{x}" y="{-16 - row * 5}" width="11" height="4.6" fill="{shade}"/>')
    bridge = "".join(f'<rect x="{x}" y="-38" width="2.4" height="2.2"/>' for x in range(-62, -48, 4))
    deck_lights = "".join(f'<circle cx="{x}" cy="-6" r="1"/>' for x in range(-60, 70, 22))
    return f"""<path d="M-78 -11L-75 -2Q-74 0 -69 0H62Q70 -3 79 -12Z" fill="{HULL}" stroke="{LINE}" stroke-width="1.1"/>
        <path d="M-73 -11V-28H-67V-11M-64 -11V-41H-46V-11M-58 -41V-47H-52V-41" fill="{DECK}" stroke="{LINE}" stroke-width="1"/>
        <path d="M-67 -41H-43M68 -12V-25M-55 -47V-53" stroke="{LINE}" stroke-width="1"/>
        <g stroke="{LINE}" stroke-opacity=".6" stroke-width=".7">{''.join(boxes)}</g>
        <circle cx="68" cy="-26" r="1.3" fill="{ACCENT}"/>
        <g fill="{WARM}">{bridge}{deck_lights}</g>"""


def ship(body, waterline, scale, secs, delay):
    """A ship sliding left past the camera, with its shadow and reflection."""
    streaks = "".join(
        f'<path class="shimmer" style="animation-delay:{-i * 0.7}s" d="M{-w / 2:g} {y}h{w}"/>'
        for i, (y, w) in enumerate(((4, 120), (9, 86), (15, 52), (22, 24))))
    return f"""<g transform="translate(0 {waterline})"><g class="pass" style="animation-duration:{secs}s;animation-delay:{delay}s"><g transform="scale({scale})">
        <ellipse cx="0" cy="2" rx="84" ry="3.5" fill="#040a14" opacity=".6"/>
        <g transform="scale(1 -.55)" opacity=".22">{body}</g>
        <g stroke="{WARM}" stroke-width="1.2" opacity=".45">{streaks}</g>
        <g class="rock">{body}</g>
      </g></g></g>"""


def build():
    b64, cw, ch, ax, ay, timeline, standing = load_sprites(LOOPS)
    frames_css, frames_secs = frame_keyframes(timeline, cw)
    n_cells = max(i for i, _ in timeline) + 1
    k = SURFER_HEIGHT / standing                     # header units per GIF pixel
    rng = random.Random(7)

    ride_x = CREST_X + FACE_LENGTH * SURFER_AT
    ride_y = wave_y(ride_x)
    ride_angle = math.degrees(math.atan(wave_slope(ride_x))) * 0.75
    foot = CREST_X + FACE_LENGTH

    hills_d = hills(rng)
    city_tile = skyline(rng)
    stars = "".join(
        f'<circle class="star" cx="{rng.randint(10, W - 10)}" cy="{rng.randint(8, CITY_BASE - 44)}" r="{rng.choice((0.8, 1, 1.2, 1.5))}"/>'
        for _ in range(26))
    face_lines = "".join(
        f'<path class="flow" style="animation-delay:{-i * 0.23:.2f}s" d="{wave_line(drop=i * 13 + i * i * 1.5)}" stroke-opacity="{0.55 - i * 0.06:.2f}"/>'
        for i in range(1, 8))
    mist = "".join(
        f'<circle class="mist" style="animation-delay:{-i * 0.21:.2f}s" cx="{CREST_X - 10 + i * 5}" cy="{CREST_Y + (i % 3) * 3}" r="{1.9 - (i % 3) * 0.4:.1f}"/>'
        for i in range(8))
    moon_x = 700
    moon_path = "".join(
        f'<path class="shimmer" style="animation-delay:{-i * 0.5}s" d="M{moon_x - w / 2:g} {y}h{w}"/>'
        for i, (y, w) in enumerate(((132, 62), (141, 48), (152, 36), (165, 24), (180, 13))))
    wake = wave_line(drop=-1.5, start=CREST_X + 26, end=int(ride_x) - 8, step=4)

    def city():
        return f'<g class="city">{city_tile}<g transform="translate({W})">{city_tile}</g></g>'

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <defs>
    <clipPath id="panel"><rect width="{W}" height="{H}" rx="12"/></clipPath>
    <linearGradient id="sky" x1="0" x2="0" y1="0" y2="{WATER}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{SKY_TOP}"/><stop offset="1" stop-color="{SKY_LOW}"/>
    </linearGradient>
    <linearGradient id="sea" x1="0" x2="0" y1="{WATER}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{SEA_TOP}"/><stop offset="1" stop-color="{SEA_LOW}"/>
    </linearGradient>
    <linearGradient id="face" x1="0" x2="0" y1="{CREST_Y}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#3f84c4"/><stop offset=".3" stop-color="#235489"/><stop offset=".7" stop-color="#12305a"/><stop offset="1" stop-color="#0a1a33"/>
    </linearGradient>
    <linearGradient id="tail" x1="{foot + 20}" x2="{foot + 230}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <mask id="fade-tail" maskUnits="userSpaceOnUse" x="-40" y="0" width="{W + 80}" height="{H + 20}"><rect x="-40" width="{W + 80}" height="{H + 20}" fill="url(#tail)"/></mask>
    <linearGradient id="wake" x1="{CREST_X + 26}" x2="{ride_x:.0f}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".85"/>
    </linearGradient>
    <radialGradient id="glow"><stop offset="0" stop-color="#cfe3ff" stop-opacity=".32"/><stop offset="1" stop-color="#cfe3ff" stop-opacity="0"/></radialGradient>
    <clipPath id="in-wave"><path d="{wave_line()}V{H + 10}H-30Z"/></clipPath>
  </defs>
  <style>
    .star {{ animation: twinkle 5s ease-in-out infinite alternate; }}
    .star:nth-child(2n) {{ animation-delay: -2s; }}
    .star:nth-child(3n) {{ animation-delay: -3.5s; }}
    .hills {{ animation: scroll 150s linear infinite; }}
    .city {{ animation: scroll 55s linear infinite; }}
    .blink {{ animation: blink 2.4s steps(1) infinite; }}
    .pass {{ animation: pass linear infinite; }}
    .rock {{ animation: rock 3.4s ease-in-out infinite alternate; }}
    .shimmer {{ animation: shimmer 1.8s ease-in-out infinite alternate; }}
    .ripple {{ animation: drift 4s linear infinite; }}
    .ripple.slow {{ animation-duration: 7s; }}
    .chop {{ animation: chop 2.6s linear infinite; }}
    .chop.near {{ animation-duration: 1.7s; }}
    .heave {{ animation: heave 3.2s ease-in-out infinite alternate; }}
    .flow {{ animation: flow 1s linear infinite; }}
    .wake {{ animation: flow .7s linear infinite; }}
    .mist {{ animation: mist 1.5s linear infinite; }}
    .bob {{ animation: bob .9s ease-in-out infinite alternate; }}
    .tilt {{ animation: tilt 1.3s ease-in-out infinite alternate; }}
    .strip {{ animation: frames {frames_secs:.3f}s step-end infinite; image-rendering: pixelated; }}
    .spray {{ animation: spray .6s linear infinite; }}
    .spray.b {{ animation-delay: -.2s; }}
    .spray.c {{ animation-delay: -.4s; }}
    @keyframes twinkle {{ from {{ opacity: 1; }} to {{ opacity: .3; }} }}
    @keyframes scroll {{ to {{ transform: translateX(-{W}px); }} }}
    @keyframes blink {{ 0% {{ opacity: 1; }} 55% {{ opacity: .15; }} }}
    @keyframes pass {{ from {{ transform: translateX({W + 150}px); }} to {{ transform: translateX(-150px); }} }}
    @keyframes rock {{ from {{ transform: rotate(-.8deg); }} to {{ transform: rotate(.8deg); }} }}
    @keyframes shimmer {{ from {{ opacity: 1; transform: translateX(-2px); }} to {{ opacity: .35; transform: translateX(2px); }} }}
    @keyframes drift {{ to {{ stroke-dashoffset: 240; }} }}
    @keyframes chop {{ to {{ transform: translateX(-141px); }} }}
    @keyframes heave {{ from {{ transform: translateY(-2px); }} to {{ transform: translateY(2px); }} }}
    @keyframes flow {{ to {{ stroke-dashoffset: 110; }} }}
    @keyframes mist {{ from {{ transform: translate(0, 0); opacity: .95; }} to {{ transform: translate(-46px, -16px); opacity: 0; }} }}
    @keyframes bob {{ from {{ transform: translateY(-1.5px); }} to {{ transform: translateY(1.5px); }} }}
    @keyframes tilt {{ from {{ transform: rotate(-2deg); }} to {{ transform: rotate(2deg); }} }}
    @keyframes frames {{ {frames_css} }}
    @keyframes spray {{ from {{ transform: translate(0, 0); opacity: .95; }} to {{ transform: translate(-46px, -8px); opacity: 0; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>

  <g clip-path="url(#panel)">
    <rect width="{W}" height="{H}" fill="url(#sky)"/>
    <g fill="#c9d6ea">{stars}</g>
    <circle cx="{moon_x}" cy="52" r="62" fill="url(#glow)"/>
    <circle cx="{moon_x}" cy="52" r="25" fill="#dbe9ff" fill-opacity=".14" stroke="{FOAM}" stroke-width="1.5"/>
    <path d="M{moon_x - 12} 37a19 19 0 0 0 3 28" stroke="{FOAM}" stroke-opacity=".5" stroke-width="1.3"/>

    <g class="hills" fill="{LAND}" stroke="{LINE}" stroke-opacity=".4" stroke-width="1">
      <path d="{hills_d}"/><path d="{hills_d}" transform="translate({W})"/>
    </g>

    <rect y="{WATER}" width="{W}" height="{H - WATER}" fill="url(#sea)"/>
    <g transform="translate(0 {WATER}) scale(1 -.5) translate(0 {-WATER})" opacity=".25">{city()}</g>
    {city()}
    <path d="M0 {WATER}H{W}" stroke="{FOAM}" stroke-opacity=".55" stroke-width="1.2" stroke-dasharray="14 6 5 9"/>

    <g stroke="{FOAM}" stroke-width="1.6" stroke-opacity=".8">{moon_path}</g>

    <g stroke="{LINE}" stroke-width="1.1" stroke-opacity=".4">
      <path class="ripple slow" d="M0 137H{W}" stroke-dasharray="40 200"/>
      <path class="ripple slow" d="M0 152H{W}" stroke-dasharray="56 184" stroke-dashoffset="120"/>
      <path class="ripple" d="M0 172H{W}" stroke-dasharray="70 170" stroke-dashoffset="60"/>
      <path class="ripple" d="M0 196H{W}" stroke-dasharray="84 156" stroke-dashoffset="150"/>
    </g>

    {ship(container_ship(), 150, 0.6, 110, -48)}
    {ship(cruise_ship(), 218, 1.35, 46, -11)}

    <path class="chop" d="{chop_line(236, 3.5, 141)}" stroke="{LINE}" stroke-opacity=".55" stroke-width="1.2"/>
    <path class="chop near" d="{chop_line(TROUGH_Y - 4, 4.5, 141)}" stroke="{ACCENT}" stroke-width="1.6"/>

    <g class="heave">
      <g mask="url(#fade-tail)">
        <path d="{wave_line()}V{H + 10}H-30Z" fill="url(#face)"/>
        <g clip-path="url(#in-wave)" stroke="{FOAM}" stroke-width="1.3" stroke-dasharray="46 64">{face_lines}</g>
        <path d="{wave_line()}" stroke="{FOAM}" stroke-width="2"/>
      </g>
      <path d="{wave_line(start=CREST_X - 34, end=CREST_X + 22, step=4)}" stroke="#fff" stroke-opacity=".9" stroke-width="3.2"/>
      <g fill="#fff">{mist}</g>
      <path class="wake" d="{wake}" stroke="url(#wake)" stroke-width="3" stroke-dasharray="16 8"/>

      <g transform="translate({ride_x:.1f} {ride_y:.1f}) rotate({ride_angle:.1f})">
        <ellipse cx="-6" cy="4" rx="40" ry="4" fill="#040a14" opacity=".5"/>
        <g class="bob"><g class="tilt">
          <g stroke="#fff" stroke-width="1.8">
            <path class="spray" d="M-30 -2h-14"/>
            <path class="spray b" d="M-34 -9h-10"/>
            <path class="spray c" d="M-26 3h-18"/>
          </g>
          <svg x="{-ax * k:.2f}" y="{-ay * k + 5:.2f}" width="{cw * k:.2f}" height="{ch * k:.2f}" viewBox="0 0 {cw} {ch}">
            <image class="strip" width="{cw * n_cells}" height="{ch}" href="data:image/png;base64,{b64}"/>
          </svg>
        </g></g>
      </g>
    </g>
  </g>
</svg>
"""
    OUT.write_text(svg, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size / 1024:.0f} KB  "
          f"({n_cells} frames, {cw}x{ch}, {frames_secs:.1f}s cycle)")


if __name__ == "__main__":
    build()
