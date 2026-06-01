import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
DAY_FULL = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]

_ASSET_DIR = Path(__file__).parent.parent / "assets" / "fonts"

# ── Layout ────────────────────────────────────────────────────────────────────
LABEL_W = 58
HEADER_H = 48
ROW_H = 120
PAD = 14
COL_W = 118
IMG_W = PAD + LABEL_W + COL_W * 7 + PAD   # 918
IMG_H = PAD + HEADER_H + ROW_H * 2 + PAD  # 316

# ── Palette ───────────────────────────────────────────────────────────────────
C_BG         = (255, 255, 255)
C_HEADER_BG  = (30,  41,  59)   # slate-800
C_HEADER_FG  = (255, 255, 255)
C_LABEL_BG   = (241, 245, 249)  # slate-100
C_LABEL_FG   = (71,  85, 105)   # slate-600
C_GRID       = (203, 213, 224)  # slate-300
C_EMPTY_BG   = (248, 250, 252)  # slate-50
C_EMPTY_FG   = (148, 163, 184)  # slate-400
C_SANG       = (234,  88,  12)  # orange-600
C_TOI        = (99,  102, 241)  # indigo-500
C_EVENT_FG   = (255, 255, 255)

_BOLD = [
    str(_ASSET_DIR / "DejaVuSans-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_REGULAR = [
    str(_ASSET_DIR / "DejaVuSans.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _center(draw: ImageDraw.ImageDraw, rect: tuple, text: str, font, color):
    x1, y1, x2, y2 = rect
    bb = draw.textbbox((0, 0), text, font=font)
    tx = x1 + (x2 - x1 - (bb[2] - bb[0])) // 2
    ty = y1 + (y2 - y1 - (bb[3] - bb[1])) // 2
    draw.text((tx, ty), text, fill=color, font=font)


def _truncate(text: str, draw: ImageDraw.ImageDraw, font, max_w: int) -> str:
    bb = draw.textbbox((0, 0), text, font=font)
    if bb[2] - bb[0] <= max_w:
        return text
    while text:
        text = text[:-1]
        bb = draw.textbbox((0, 0), text + "…", font=font)
        if bb[2] - bb[0] <= max_w:
            return text + "…"
    return "…"


def generate(schedule: dict, display_name: str) -> io.BytesIO:
    f_hd  = _font(_BOLD,    14)
    f_bd  = _font(_REGULAR, 13)
    f_sm  = _font(_REGULAR, 11)

    img  = Image.new("RGB", (IMG_W, IMG_H), C_BG)
    draw = ImageDraw.Draw(img)

    x0 = PAD
    yh = PAD  # top of header row

    # ── Header row ───────────────────────────────────────────────────────────
    draw.rectangle([x0, yh, x0 + LABEL_W, yh + HEADER_H], fill=C_HEADER_BG)
    for i, day in enumerate(DAY_FULL):
        cx = x0 + LABEL_W + i * COL_W
        draw.rectangle([cx, yh, cx + COL_W, yh + HEADER_H], fill=C_HEADER_BG)
        _center(draw, (cx, yh, cx + COL_W, yh + HEADER_H), day, f_hd, C_HEADER_FG)

    # ── Data rows ─────────────────────────────────────────────────────────────
    for pi, (pkey, plabel, pcolor) in enumerate([
        ("sang", "Sáng", C_SANG),
        ("toi",  "Tối",  C_TOI),
    ]):
        ry = yh + HEADER_H + pi * ROW_H

        # Row label
        draw.rectangle([x0, ry, x0 + LABEL_W, ry + ROW_H], fill=C_LABEL_BG)
        _center(draw, (x0, ry, x0 + LABEL_W, ry + ROW_H), plabel, f_hd, C_LABEL_FG)

        for i, dkey in enumerate(DAYS):
            cx = x0 + LABEL_W + i * COL_W
            entry = schedule[dkey][pkey]

            draw.rectangle([cx, ry, cx + COL_W, ry + ROW_H], fill=C_EMPTY_BG)

            if entry and entry.get("task"):
                EP = 7
                ex1, ey1 = cx + EP, ry + EP
                ex2, ey2 = cx + COL_W - EP, ry + ROW_H - EP
                draw.rounded_rectangle([ex1, ey1, ex2, ey2], radius=8, fill=pcolor)

                max_w = ex2 - ex1 - 12
                task = _truncate(entry["task"], draw, f_bd, max_w)
                draw.text((ex1 + 7, ey1 + 8), task, fill=C_EVENT_FG, font=f_bd)

                from_t = entry.get("from", "")
                to_t   = entry.get("to", "")
                if from_t or to_t:
                    ts = f"{from_t} – {to_t}" if (from_t and to_t) else (from_t or to_t)
                    bb = draw.textbbox((0, 0), ts, font=f_sm)
                    draw.text((ex1 + 7, ey2 - (bb[3] - bb[1]) - 7), ts, fill=C_EVENT_FG, font=f_sm)
            else:
                _center(draw, (cx, ry, cx + COL_W, ry + ROW_H), "—", f_bd, C_EMPTY_FG)

    # ── Grid lines ────────────────────────────────────────────────────────────
    grid_r = x0 + LABEL_W + COL_W * 7
    grid_b = yh + HEADER_H + ROW_H * 2

    # verticals
    draw.line([(x0 + LABEL_W, yh), (x0 + LABEL_W, grid_b)], fill=C_GRID, width=1)
    for i in range(1, 7):
        lx = x0 + LABEL_W + i * COL_W
        draw.line([(lx, yh), (lx, grid_b)], fill=C_GRID, width=1)

    # horizontals
    for ly in [yh + HEADER_H, yh + HEADER_H + ROW_H]:
        draw.line([(x0, ly), (grid_r, ly)], fill=C_GRID, width=1)

    # outer border
    draw.rectangle([x0, yh, grid_r, grid_b], outline=C_GRID, width=2)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
