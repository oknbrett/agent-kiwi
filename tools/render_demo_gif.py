"""Render the captured simulate_week.py output into the README demo GIF.

    python tools/render_demo_gif.py assets/week_output.txt assets/demo.gif

Deterministic on purpose: the GIF is generated from a captured real run
(assets/week_output.txt), not screen-recorded, so it can be regenerated
exactly when the output changes. Each day's coach digest is shown as a
terminal "page"; Friday — the escalation — holds longest.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Look ──────────────────────────────────────────────────────────────────────
W, H = 920, 600
PAD_X, PAD_Y = 22, 16
TITLEBAR_H = 34
LINE_H = 19
FONT_SIZE = 13
WRAP_COLS = 104

BG = (8, 9, 10)
TITLEBAR = (18, 19, 22)
FRAME_LINE = (32, 35, 40)
TEXT = (200, 204, 212)
DIM = (108, 113, 124)
GREEN = (181, 232, 77)  # kiwi
RED = (255, 105, 100)
AMBER = (240, 169, 60)
CYAN = (120, 200 - 20, 200)

FONT_PATH = "C:/Windows/Fonts/consola.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/consolab.ttf"

HOLD_TYPING_MS = 90
HOLD_DAY_MS = 2600
HOLD_FRIDAY_MS = 7000
HOLD_END_MS = 4000


def load_fonts():
    return (
        ImageFont.truetype(FONT_PATH, FONT_SIZE),
        ImageFont.truetype(FONT_BOLD_PATH, FONT_SIZE),
    )


def sanitize(line: str) -> str:
    return line.replace("⚠", "!").replace("\t", "    ")


def wrap(line: str, cols: int = WRAP_COLS) -> list[str]:
    if len(line) <= cols:
        return [line]
    indent = (len(line) - len(line.lstrip())) * " "
    cont_indent = indent + "    "
    out, cur = [], ""
    for word in line.split(" "):
        candidate = f"{cur} {word}".strip() if cur else word
        prefix = indent if not out else cont_indent
        if len(prefix) + len(candidate) > cols and cur:
            out.append((indent if not out else cont_indent) + cur.strip())
            cur = word
        else:
            cur = candidate
    if cur:
        out.append((indent if not out else cont_indent) + cur.strip())
    return out


def color_for(line: str):
    s = line.strip()
    if s.startswith("Coach digest"):
        return GREEN, True
    if s.startswith("="):
        return FRAME_LINE, False
    if s.startswith("ACTION NEEDED"):
        return RED, True
    if s.startswith("!") or s.startswith("→"):
        return RED, False
    if s.startswith("(client said"):
        return DIM, False
    if s.startswith("KEEPING AN EYE ON"):
        return AMBER, True
    if s.startswith("•"):
        return AMBER, False
    if s.startswith("EVERYONE ELSE") or s.startswith("No escalations"):
        return DIM, True
    if s.startswith("-"):
        return TEXT, False
    return TEXT, False


def base_frame(fonts) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, TITLEBAR_H], fill=TITLEBAR)
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([14 + i * 22, 11, 26 + i * 22, 23], fill=c)
    d.text((W // 2 - 60, 9), "agent-kiwi — demo", font=fonts[0], fill=DIM)
    return img


def draw_lines(img: Image.Image, fonts, lines, start_y=None) -> Image.Image:
    img = img.copy()
    d = ImageDraw.Draw(img)
    y = start_y if start_y is not None else TITLEBAR_H + PAD_Y
    font, bold = fonts
    for raw in lines:
        for line in wrap(sanitize(raw)):
            color, is_bold = color_for(line)
            d.text((PAD_X, y), line, font=bold if is_bold else font, fill=color)
            y += LINE_H
    return img


def prompt_frames(fonts) -> list[tuple[Image.Image, int]]:
    """A short typing animation for `python simulate_week.py`."""
    cmd = "python simulate_week.py"
    frames = []
    for n in (8, 14, len(cmd)):
        img = base_frame(fonts)
        d = ImageDraw.Draw(img)
        y = TITLEBAR_H + PAD_Y
        d.text((PAD_X, y), "$ ", font=fonts[1], fill=GREEN)
        d.text((PAD_X + 18, y), cmd[:n] + "▌", font=fonts[0], fill=TEXT)
        frames.append((img, HOLD_TYPING_MS if n < len(cmd) else 700))
    return frames


def main() -> int:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    text = src.read_text(encoding="utf-8-sig")

    # Split into per-day digests on the header line.
    days: list[list[str]] = []
    for raw_line in text.splitlines():
        if raw_line.startswith("Coach digest"):
            days.append([])
        if days:
            days[-1].append(raw_line.rstrip())

    fonts = load_fonts()
    frames: list[tuple[Image.Image, int]] = prompt_frames(fonts)

    for i, day in enumerate(days):
        is_friday = i == len(days) - 1
        header = [f"$ python simulate_week.py", ""]
        img = base_frame(fonts)
        d = ImageDraw.Draw(img)
        d.text((PAD_X, TITLEBAR_H + PAD_Y), "$ python simulate_week.py", font=fonts[0], fill=DIM)
        img = draw_lines(img, fonts, day, start_y=TITLEBAR_H + PAD_Y + 2 * LINE_H)
        if is_friday:
            # Hold Friday's escalation, then an annotated end card on top of it.
            frames.append((img, HOLD_FRIDAY_MS))
            end = img.copy()
            d = ImageDraw.Draw(end)
            d.rectangle([PAD_X, H - 64, W - PAD_X, H - 26], fill=TITLEBAR, outline=GREEN)
            d.text(
                (PAD_X + 14, H - 54),
                "Kiwi escalated Sofia's post-surgical pain — and left Maya's DOMS alone.",
                font=fonts[1],
                fill=GREEN,
            )
            frames.append((end, HOLD_END_MS))
        else:
            frames.append((img, HOLD_DAY_MS))

    imgs = [f for f, _ in frames]
    durations = [ms for _, ms in frames]
    imgs[0].save(
        dst,
        save_all=True,
        append_images=imgs[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"wrote {dst} ({dst.stat().st_size // 1024} KB, {len(imgs)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
