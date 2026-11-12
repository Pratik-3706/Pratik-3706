"""Builds assets/header.svg: a night sea with a pixel-art surfer riding a tall wave.

Usage:  python scripts/build_header.py

The surfer is read from GIF loops, packed into one sprite strip and embedded in
the SVG, so the header is a single self-contained file that GitHub can show in
a README. Everything that moves is plain CSS inside the SVG.

The sky turns from night to day and back, starting at night.

The waves roll to the right, the way she is heading, and she rises and tilts
with each one. The coast and the ships slide past to the left.
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
SURF = ASSETS / "Chibi Furina Surfing Loop.gif"
LOOPS = [
    (SURF, 2, 1.35, True),
    (ASSETS / "Chibi Surfer’s Animated Board Grab.gif", 1, 1.2, False),
    (SURF, 2, 1.35, True),
    (ASSETS / "Chibi Surfboard Spin Animation.gif", 1, 1.2, False),
]
SURFER_HEIGHT = 128   # drawn height of her standing pose, in header units

W, H = 846, 300
# How much of the scene the header shows. 1 shows all of it; above 1 crops in,
# keeping the bottom edge and trimming the sky and a little off each side.
ZOOM = 1.1
VIEW_W, VIEW_H = W / ZOOM, H / ZOOM
VIEW_X, VIEW_Y = (W - VIEW_W) * 0.4, H - VIEW_H
WATER = 126           # where the sea meets the coast
CITY_BASE = 104       # top of the sea wall the city stands on

# Colours. The scene has its own night sky, so it looks the same on any theme.
SKY_TOP, SKY_LOW = "#070d1a", "#14294a"
SEA_TOP, SEA_LOW = "#10233f", "#081326"
LAND, QUAY = "#0c1830", "#1a2a45"
HULL, DECK = "#0d1a2e", "#1b2d49"
LINE = "#8b9bb4"
ACCENT = "#5aa9e6"
FOAM = "#b5d9ff"
WARM = "#f2c14e"

# Day and night. One full turn of the sky takes CYCLE seconds and starts at
# night. Each entry is a part of the scene and what changes about it:
#   property: (at night, by day, at dawn and dusk)   -- the last one is optional
CYCLE = 48
DAYLIGHT = {
    "sky-top": {"stop-color": ("#070d1a", "#4d9be0", "#3a3565")},
    "sky-low": {"stop-color": ("#14294a", "#c4e6fb", "#f2a66e")},
    "sea-top": {"stop-color": ("#10233f", "#63b2e6", "#8a6f8c")},
    "sea-low": {"stop-color": ("#081326", "#2c78bd", "#26335e")},
    "face-a": {"stop-color": ("#2c629c", "#8ad0f5", None)},
    "face-b": {"stop-color": ("#163a67", "#3f96d8", None)},
    "face-c": {"stop-color": ("#0a1a33", "#1f62a6", None)},
    "stars": {"opacity": (1, 0, .25)},
    "hill": {"fill": ("#0c1830", "#7fa596", "#4a4f72")},
    "town": {"fill": ("#0c1830", "#ece6d8", "#6b5f78"), "stroke": ("#8b9bb4", "#5a6a82", "#8b8ba4")},
    "quay": {"fill": ("#1a2a45", "#bdb6a6", "#6d6478")},
    "rocks": {"fill": ("#0c1830", "#808a96", "#4a4a66")},
    "lamp": {"opacity": (1, .1, .8)},     # windows and lamps go dark by day
    "glow": {"opacity": (1, 0, .6)},      # and their reflections go with them
    "hull": {"fill": ("#0d1a2e", "#27405f", None)},
    "deck": {"fill": ("#1b2d49", "#f3f6fa", None)},
    "dusk": {"opacity": (0, 0, .75)},     # the warm band on the horizon
}

# The waves she rides: a rolling swell that travels right, under her board.
SURFER_X = 200
WAVE_Y, WAVE_AMP, WAVE_PERIOD, WAVE_SECS = 250, 14, 423, 4.0
BOARD_SINK = 11       # how far the bottom of the board sits under the surface

# --- surfer ----------------------------------------------------------------

def load_sprites(loops):
    """Packs every frame of every loop into one strip.

    Returns (base64 png, cell w, cell h, anchor x, anchor y, timeline, standing h)
    where the anchor is the point of a cell that sits on the water and the
    timeline is a list of (frame index, seconds, lands). `lands` marks the frame
    of a trick where the board comes back down onto the water.
    """
    placed, timeline, standing, seen = [], [], None, {}
    for path, times, speed, pin in loops:
        if path not in seen:
            gif = Image.open(path)
            frames, secs = [], []
            for i in range(gif.n_frames):
                gif.seek(i)
                secs.append(gif.info.get("duration", 100) / 1000 / speed)
                frames.append(gif.convert("RGBA"))
            boxes = [f.getbbox() for f in frames]
            anchor_x = (boxes[0][0] + boxes[0][2]) // 2
            if standing is None:
                standing = boxes[0][3] - boxes[0][1]
            # How far the board is off the water in each frame, and the frame
            # after the highest point where it has dropped most of the way back.
            lift = [boxes[0][3] - b[3] for b in boxes]
            landing = None
            if not pin and max(lift) > 8:
                peak = lift.index(max(lift))
                landing = next((i for i in range(peak + 1, len(lift)) if lift[i] < max(lift) / 2), None)
            seen[path] = (len(placed), secs, landing)
            for f, b in zip(frames, boxes):
                foot = b[3] if pin else boxes[0][3]
                placed.append((f.crop(b), b[0] - anchor_x, b[1] - foot))
        first, secs, landing = seen[path]
        for _ in range(times):
            timeline += [(first + i, t, i == landing) for i, t in enumerate(secs)]

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
    total = sum(t for _, t, _ in timeline)
    out, now = [], 0.0
    for idx, secs, _ in timeline:
        out.append(f"{now / total * 100:.3f}% {{ transform: translateX(-{idx * cw}px); }}")
        now += secs
    out.append(f"100% {{ transform: translateX(-{timeline[0][0] * cw}px); }}")
    return " ".join(out), total


def splash_keyframes(timeline, burst=0.6):
    """CSS keyframes that throw up a splash each time a trick lands."""
    total = sum(t for _, t, _ in timeline)
    hidden = "opacity: 0; transform: scale(.45);"
    out, now = [f"0% {{ {hidden} }}"], 0.0
    for _, secs, lands in timeline:
        if lands:
            a, b = now / total * 100, min(99.9, (now + burst) / total * 100)
            out += [f"{a - 0.01:.3f}% {{ {hidden} }}",
                    f"{a:.3f}% {{ opacity: 1; transform: scale(.45); }}",
                    f"{(a + b) / 2:.3f}% {{ opacity: .95; transform: scale(1); }}",
                    f"{b:.3f}% {{ opacity: 0; transform: scale(1.25); }}",
                    f"{b + 0.01:.3f}% {{ {hidden} }}"]
        now += secs
    out.append(f"100% {{ {hidden} }}")
    return " ".join(out)


SUNRISE, SUNSET = 36, 89          # percent of the cycle; the moon has the rest


def sky_xy(u):
    """Where the sun or moon is, u=0 rising on the right to u=1 setting on the left."""
    return W - 56 - (W - 112) * u, 150 - 92 * math.sin(math.pi * u)


def sky_keyframes(body, steps=12):
    """CSS keyframes that carry the sun or the moon over the sky in a low arc.

    Both wait below the horizon, hidden behind the sea, while the other is up.
    """
    def at(pct, u):
        x, y = sky_xy(u)
        return f"{pct:.2f}% {{ transform: translate({x:.1f}px, {y:.1f}px); }}"

    day, night = SUNSET - SUNRISE, 100 - (SUNSET - SUNRISE)
    if body == "sun":
        frames = [at(0, 0)] + [at(SUNRISE + day * i / steps, i / steps) for i in range(steps + 1)] + [at(100, 1)]
    else:
        start = (100 - SUNSET) / night            # the moon is already up when the cycle begins
        up = [at(SUNRISE * i / steps, start + (1 - start) * i / steps) for i in range(steps + 1)]
        down = [at(SUNSET + (100 - SUNSET) * i / 4, start * i / 4) for i in range(5)]
        frames = up + down
    return " ".join(frames)


def daylight_css():
    """CSS that carries every part of the scene from night to day and back."""
    out = []
    for name, props in DAYLIGHT.items():
        def at(i):
            return " ".join(f"{prop}: {v[i]};" for prop, v in props.items())
        twilight = all(v[2] is not None for v in props.values())
        steps = [f"0%, 32% {{ {at(0)} }}"]
        if twilight:
            steps.append(f"38% {{ {at(2)} }}")
        steps.append(f"44%, 81% {{ {at(1)} }}")
        if twilight:
            steps.append(f"87% {{ {at(2)} }}")
        steps.append(f"93%, 100% {{ {at(0)} }}")
        out.append(f".c-{name} {{ animation: c-{name} {CYCLE}s linear infinite; }} "
                   f"@keyframes c-{name} {{ {' '.join(steps)} }}")
    return "\n    ".join(out)


# --- water -----------------------------------------------------------------

def wave_path(y, amp, period, crest_x, drop=0, close_to=None):
    """An even sine wave with a crest at crest_x once it has scrolled a full period."""
    start, end = -int(period) - 6, W + int(period) + 6
    pts = [(x, y + drop - amp * math.cos(2 * math.pi * (x - crest_x) / period))
           for x in range(start, end + 1, 6)]
    d = "M" + "L".join(f"{x} {py:.2f}" for x, py in pts)
    if close_to is not None:
        d += f"V{close_to}H{start}Z"
    return d


def ride_keyframes(amp, period, tilt=1.0, steps=24):
    """Keeps something on the wave: its height and its slope at every moment.

    tilt below 1 leans it less than the water does, for long hulls.
    """
    out = []
    for i in range(steps + 1):
        f = i / steps
        y = -amp * math.cos(2 * math.pi * f)
        slope = -amp * 2 * math.pi / period * math.sin(2 * math.pi * f)
        out.append(f"{f * 100:.2f}% {{ transform: translateY({y:.2f}px) rotate({math.degrees(math.atan(slope)) * tilt:.2f}deg); }}")
    return " ".join(out)


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
    d, lights, glints, x = [f"M0 {base}"], [], [], 0
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
                glints.append((lx + 0.8, 0.6))
        x += w
    d.append(f"V{base}H0Z")

    # The coast itself: a sea wall with buttresses and street lamps, rocks at
    # its foot, and a lighthouse standing on it.
    lamps = "".join(f'<circle cx="{lx}" cy="{base - 2.5}" r="1.1"/>' for lx in range(14, W, 47))
    buttresses = "".join(f"M{bx} {base}V{WATER - 5}" for bx in range(30, W, 47))
    rocks, rx = [f"M0 {WATER}"], 0
    while rx < W:
        rw = rng.randint(9, 22)
        rocks.append(f"Q{rx + rw / 2:g} {WATER - rng.randint(4, 9)} {min(W, rx + rw)} {WATER - rng.randint(0, 2)}")
        rx += rw
    rocks.append(f"V{WATER}Z")
    lx = 610
    lighthouse = (
        f'<path d="M{lx - 5} {base}L{lx - 3} {base - 34}H{lx + 3}L{lx + 5} {base}Z'
        f'M{lx - 4} {base - 34}V{base - 40}H{lx + 4}V{base - 34}M{lx - 5} {base - 40}L{lx} {base - 45}L{lx + 5} {base - 40}" '
        f'class="c-town" fill="{LAND}" stroke="{LINE}" stroke-opacity=".8" stroke-width="1"/>'
        f'<g class="c-lamp"><g class="blink" fill="{WARM}"><circle cx="{lx}" cy="{base - 37}" r="2"/>'
        f'<circle cx="{lx}" cy="{base - 37}" r="8" opacity=".25"/></g></g>')
    # Every light on shore throws a broken streak down the water toward us.
    glints += [(gx, 1.0) for gx in range(14, W, 47)]
    rows = ((4, 7, .6), (9, 6, .48), (15, 5, .36), (22, 4, .26), (30, 3, .17))
    reflection = ""
    for i, (dy, width, alpha) in enumerate(rows):
        dashes = "".join(
            f"M{gx - width * size / 2:.1f} {WATER + dy}h{width * size:.1f}"
            for gx, size in glints if size == 1.0 or i < 3)
        reflection += (f'<path class="shimmer" style="animation-delay:{-i * 0.45:.2f}s" d="{dashes}" '
                       f'stroke="{WARM}" stroke-opacity="{alpha}" stroke-width="1.3"/>')
    beam = "".join(f"M{lx - w / 2:g} {WATER + dy}h{w}" for dy, w in ((5, 12), (11, 10), (18, 8), (26, 6), (35, 4)))
    reflection += f'<path class="blink" d="{beam}" stroke="{WARM}" stroke-opacity=".7" stroke-width="1.6"/>'

    return (
        f'<path class="c-town" d="{"".join(d)}" fill="{LAND}" stroke="{LINE}" stroke-opacity=".75" stroke-width="1"/>'
        f'<g class="c-lamp" fill="{WARM}">{"".join(lights)}</g>{lighthouse}'
        f'<rect class="c-quay" y="{base}" width="{W}" height="{WATER - base}" fill="{QUAY}"/>'
        f'<path d="{buttresses}" stroke="{LINE}" stroke-opacity=".3" stroke-width="1"/>'
        f'<path d="M0 {base}H{W}" stroke="{LINE}" stroke-opacity=".9" stroke-width="1.2"/>'
        f'<path class="c-rocks" d="{"".join(rocks)}" fill="{LAND}" stroke="{LINE}" stroke-opacity=".45" stroke-width="1"/>'
        f'<g class="c-lamp" fill="{WARM}">{lamps}</g>'), reflection


def cruise_ship():
    """A cruise liner, bow to the right, waterline on y=0. About 160 long."""
    decks = ((-70, 56, -16, -23), (-64, 47, -23, -30), (-56, 38, -30, -37), (-44, 26, -37, -43))
    deck_d = "".join(f"M{x0} {yb}H{x1}L{x1 - 5} {yt}H{x0 + 2}Z" for x0, x1, yb, yt in decks)
    windows = "".join(
        f'<rect x="{x}" y="{yt + 2.2}" width="2.6" height="2.2"/>'
        for x0, x1, yb, yt in decks for x in range(x0 + 5, x1 - 9, 6))
    ports = "".join(f'<circle cx="{x}" cy="-8" r="1.1"/>' for x in range(-66, 62, 8))
    return f"""<path d="M-78 -15L-74 -2Q-73 0 -68 0H60Q69 -4 80 -17Z" class="c-hull" fill="{HULL}" stroke="{LINE}" stroke-width="1.1"/>
        <path d="M-76 -6H66" stroke="{ACCENT}" stroke-opacity=".6" stroke-width="1"/>
        <path d="{deck_d}M-38 -43L-36 -57H-24L-21 -43Z" class="c-deck" fill="{DECK}" stroke="{LINE}" stroke-width="1"/>
        <path d="M-36.500 -52H-23M12 -43V-56M7 -51H17" stroke="{ACCENT}" stroke-width="1.2"/>
        <circle cx="12" cy="-57.500" r="1.4" fill="{ACCENT}"/>
        <g class="c-lamp" fill="{WARM}">{windows}{ports}</g>"""


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
    return f"""<path d="M-78 -11L-75 -2Q-74 0 -69 0H62Q70 -3 79 -12Z" class="c-hull" fill="{HULL}" stroke="{LINE}" stroke-width="1.1"/>
        <path d="M-73 -11V-28H-67V-11M-64 -11V-41H-46V-11M-58 -41V-47H-52V-41" class="c-deck" fill="{DECK}" stroke="{LINE}" stroke-width="1"/>
        <path d="M-67 -41H-43M68 -12V-25M-55 -47V-53" stroke="{LINE}" stroke-width="1"/>
        <g stroke="{LINE}" stroke-opacity=".6" stroke-width=".7">{''.join(boxes)}</g>
        <circle cx="68" cy="-26" r="1.3" fill="{ACCENT}"/>
        <g class="c-lamp" fill="{WARM}">{bridge}{deck_lights}</g>"""


def ship(body, waterline, scale, secs, delay):
    """A ship sliding left past the camera, with its shadow and reflection."""
    streaks = "".join(
        f'<path class="shimmer" style="animation-delay:{-i * 0.7}s" d="M{-w / 2:g} {y}h{w}"/>'
        for i, (y, w) in enumerate(((4, 120), (9, 86), (15, 52), (22, 24))))
    return f"""<g transform="translate(0 {waterline})"><g class="pass" style="animation-duration:{secs}s;animation-delay:{delay}s"><g transform="scale({scale})">
        <ellipse cx="0" cy="2" rx="84" ry="3.5" fill="#040a14" opacity=".6"/>
        <g transform="scale(1 -.55)" opacity=".22">{body}</g>
        <g class="c-glow"><g stroke="{WARM}" stroke-width="1.2" opacity=".45">{streaks}</g></g>
        <g class="rock">{body}</g>
      </g></g></g>"""


def build():
    b64, cw, ch, ax, ay, timeline, standing = load_sprites(LOOPS)
    frames_css, frames_secs = frame_keyframes(timeline, cw)
    n_cells = max(i for i, _, _ in timeline) + 1
    splash_css = splash_keyframes(timeline)
    k = SURFER_HEIGHT / standing                     # header units per GIF pixel
    rng = random.Random(7)

    ride_css = ride_keyframes(WAVE_AMP, WAVE_PERIOD)
    crest = WAVE_Y - WAVE_AMP

    hills_d = hills(rng)
    city_tile, city_glints = skyline(rng)
    stars = "".join(
        f'<circle class="star" cx="{rng.randint(10, W - 10)}" cy="{rng.randint(8, CITY_BASE - 44)}" r="{rng.choice((0.8, 1, 1.2, 1.5))}"/>'
        for _ in range(26))
    moon_x = round(sky_xy((100 - SUNSET) / (100 - (SUNSET - SUNRISE)))[0])   # under the moon at the start
    moon_path = "".join(
        f'<path class="shimmer" style="animation-delay:{-i * 0.5}s" d="M{moon_x - w / 2:g} {y}h{w}"/>'
        for i, (y, w) in enumerate(((132, 62), (141, 48), (152, 36), (165, 24), (180, 13))))
    def city():
        return f'<g class="city">{city_tile}<g transform="translate({W})">{city_tile}</g></g>'

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEW_X:.1f} {VIEW_Y:.1f} {VIEW_W:.1f} {VIEW_H:.1f}" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <defs>
    <clipPath id="panel"><rect x="{VIEW_X:.1f}" y="{VIEW_Y:.1f}" width="{VIEW_W:.1f}" height="{VIEW_H:.1f}" rx="11"/></clipPath>
    <linearGradient id="sky" x1="0" x2="0" y1="0" y2="{WATER}" gradientUnits="userSpaceOnUse">
      <stop class="c-sky-top" offset="0" stop-color="{SKY_TOP}"/><stop class="c-sky-low" offset="1" stop-color="{SKY_LOW}"/>
    </linearGradient>
    <linearGradient id="sea" x1="0" x2="0" y1="{WATER}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop class="c-sea-top" offset="0" stop-color="{SEA_TOP}"/><stop class="c-sea-low" offset="1" stop-color="{SEA_LOW}"/>
    </linearGradient>
    <linearGradient id="face" x1="0" x2="0" y1="{crest}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop class="c-face-a" offset="0" stop-color="#2c629c"/><stop class="c-face-b" offset=".45" stop-color="#163a67"/><stop class="c-face-c" offset="1" stop-color="#0a1a33"/>
    </linearGradient>
    <linearGradient id="cityglow" x1="0" x2="0" y1="{WATER}" y2="{WATER + 44}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{WARM}" stop-opacity=".13"/><stop offset="1" stop-color="{WARM}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="shade" x1="0" x2="0" y1="{WATER}" y2="{WATER + 10}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#040a14" stop-opacity=".6"/><stop offset="1" stop-color="#040a14" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="dusk" x1="0" x2="0" y1="{WATER - 80}" y2="{WATER}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#ff9a5a" stop-opacity="0"/><stop offset="1" stop-color="#ff9a5a" stop-opacity=".6"/>
    </linearGradient>
    <radialGradient id="sunglow"><stop offset="0" stop-color="#ffe9a8" stop-opacity=".7"/><stop offset="1" stop-color="#ffe9a8" stop-opacity="0"/></radialGradient>
    <clipPath id="below"><rect x="-160" y="2" width="320" height="170"/></clipPath>
    <image id="sheet" width="{cw * n_cells}" height="{ch}" href="data:image/png;base64,{b64}"/>
    <radialGradient id="glow"><stop offset="0" stop-color="#cfe3ff" stop-opacity=".32"/><stop offset="1" stop-color="#cfe3ff" stop-opacity="0"/></radialGradient>
  </defs>
  <style>
    .star {{ animation: twinkle 5s ease-in-out infinite alternate; }}
    .star:nth-child(2n) {{ animation-delay: -2s; }}
    .star:nth-child(3n) {{ animation-delay: -3.5s; }}
    {daylight_css()}
    .sun {{ animation: sun {CYCLE}s linear infinite; }}
    .moon {{ animation: moon {CYCLE}s linear infinite; }}
    .c-moonpath {{ animation: moonpath {CYCLE}s linear infinite; }}
    @keyframes sun {{ {sky_keyframes("sun")} }}
    @keyframes moon {{ {sky_keyframes("moon")} }}
    @keyframes moonpath {{ 0% {{ opacity: 1; }} 7%, 95% {{ opacity: 0; }} 100% {{ opacity: 1; }} }}
    .hills {{ animation: scroll 150s linear infinite; }}
    .city {{ animation: scroll 55s linear infinite; }}
    .blink {{ animation: blink 2.4s steps(1) infinite; }}
    .pass {{ animation: pass linear infinite; }}
    .rock {{ animation: rock 3.4s ease-in-out infinite alternate; }}
    .shimmer {{ animation: shimmer 1.8s ease-in-out infinite alternate; }}
    .ripple {{ animation: drift 4s linear infinite; }}
    .ripple.slow {{ animation-duration: 7s; }}
    .wave {{ animation: wave {WAVE_SECS}s linear infinite; }}
    .ride {{ animation: ride {WAVE_SECS}s linear infinite; }}
    .splash {{ animation: splash {frames_secs:.3f}s linear infinite; }}
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
    @keyframes drift {{ to {{ stroke-dashoffset: -240; }} }}
    @keyframes wave {{ from {{ transform: translateX(-{WAVE_PERIOD}px); }} to {{ transform: translateX(0); }} }}
    @keyframes ride {{ {ride_css} }}
    @keyframes frames {{ {frames_css} }}
    @keyframes splash {{ {splash_css} }}
    @keyframes spray {{ from {{ transform: translate(0, 0); opacity: .95; }} to {{ transform: translate(-46px, -8px); opacity: 0; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
  </style>

  <g clip-path="url(#panel)">
    <rect width="{W}" height="{H}" fill="url(#sky)"/>
    <g class="c-stars" fill="#c9d6ea">{stars}</g>
    <g class="moon">
      <circle r="62" fill="url(#glow)"/>
      <circle r="25" fill="#dbe9ff" fill-opacity=".14" stroke="{FOAM}" stroke-width="1.5"/>
      <path d="M-12 -15a19 19 0 0 0 3 28" stroke="{FOAM}" stroke-opacity=".5" stroke-width="1.3"/>
    </g>
    <g class="sun">
      <circle r="78" fill="url(#sunglow)"/>
      <circle r="22" fill="#ffe08a"/>
      <circle r="22" stroke="#fff3c4" stroke-width="1.5"/>
    </g>
    <rect class="c-dusk" y="{WATER - 80}" width="{W}" height="80" fill="url(#dusk)"/>

    <g class="hills" fill="{LAND}" stroke="{LINE}" stroke-opacity=".4" stroke-width="1">
      <path class="c-hill" d="{hills_d}"/><path class="c-hill" d="{hills_d}" transform="translate({W})"/>
    </g>

    <rect y="{WATER}" width="{W}" height="{H - WATER}" fill="url(#sea)"/>
    {city()}
    <rect y="{WATER}" width="{W}" height="10" fill="url(#shade)"/>
    <g class="c-glow">
      <rect y="{WATER}" width="{W}" height="44" fill="url(#cityglow)"/>
      <g class="city">{city_glints}<g transform="translate({W})">{city_glints}</g></g>
    </g>

    <g class="c-moonpath" stroke="{FOAM}" stroke-width="1.6" stroke-opacity=".8">{moon_path}</g>

    <g stroke="{LINE}" stroke-width="1.1" stroke-opacity=".4">
      <path class="ripple slow" d="M0 137H{W}" stroke-dasharray="40 200"/>
      <path class="ripple slow" d="M0 152H{W}" stroke-dasharray="56 184" stroke-dashoffset="120"/>
      <path class="ripple" d="M0 172H{W}" stroke-dasharray="70 170" stroke-dashoffset="60"/>
      <path class="ripple" d="M0 196H{W}" stroke-dasharray="84 156" stroke-dashoffset="150"/>
    </g>

    {ship(container_ship(), 150, 0.6, 110, -48)}
    {ship(cruise_ship(), 218, 1.35, 46, -11)}

    <g transform="translate({SURFER_X} {WAVE_Y})">
      <g class="ride">
        <svg x="{-ax * k:.2f}" y="{-ay * k + BOARD_SINK:.2f}" width="{cw * k:.2f}" height="{ch * k:.2f}" viewBox="0 0 {cw} {ch}">
          <use class="strip" href="#sheet"/>
        </svg>
      </g>
    </g>

    <path class="wave" d="{wave_path(WAVE_Y, WAVE_AMP, WAVE_PERIOD, SURFER_X, close_to=H + 10)}" fill="url(#face)"/>
    <g transform="translate({SURFER_X} {WAVE_Y})">
      <g class="ride"><g clip-path="url(#below)" opacity=".3"><g transform="scale(1 -.75)">
        <svg x="{-ax * k:.2f}" y="{-ay * k + BOARD_SINK:.2f}" width="{cw * k:.2f}" height="{ch * k:.2f}" viewBox="0 0 {cw} {ch}">
          <use class="strip" href="#sheet"/>
        </svg>
      </g></g></g>
    </g>
    <path class="wave" d="{wave_path(WAVE_Y, WAVE_AMP, WAVE_PERIOD, SURFER_X, drop=13)}" stroke="{FOAM}" stroke-opacity=".28" stroke-width="1.3"/>
    <path class="wave" d="{wave_path(WAVE_Y, WAVE_AMP, WAVE_PERIOD, SURFER_X, drop=28)}" stroke="{FOAM}" stroke-opacity=".14" stroke-width="1.3"/>
    <path class="wave" d="{wave_path(WAVE_Y, WAVE_AMP, WAVE_PERIOD, SURFER_X)}" stroke="{FOAM}" stroke-width="2"/>

    <g transform="translate({SURFER_X} {WAVE_Y})">
      <g class="ride">
        <g stroke="#fff" stroke-width="1.8">
          <path class="spray" d="M-30 -2h-14"/>
          <path class="spray b" d="M-34 -9h-10"/>
          <path class="spray c" d="M-26 3h-18"/>
        </g>
        <g class="splash" stroke="#fff" stroke-width="3">
          <path d="M-72 6q72 -18 144 0M-42 0q-14 -30 -44 -36M-29 -4q-8 -38 -30 -52M-14 -7q-2 -30 -11 -44M40 0q14 -28 40 -32M27 -4q7 -34 26 -46M12 -7q3 -26 10 -38"/>
          <g fill="#fff" stroke="none"><circle cx="-91" cy="-41" r="3.4"/><circle cx="-63" cy="-61" r="3"/><circle cx="-27" cy="-57" r="2.6"/><circle cx="85" cy="-37" r="3.4"/><circle cx="57" cy="-55" r="3"/><circle cx="24" cy="-51" r="2.6"/><circle cx="-78" cy="-18" r="2.2"/><circle cx="70" cy="-14" r="2.2"/><circle cx="-46" cy="-74" r="2"/><circle cx="42" cy="-68" r="2"/></g>
        </g>
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
