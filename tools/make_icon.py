"""Draws the Tiny Recorder icon (Pillow): a dark rounded tile, a red record dot with a soft ring, and two sound waves.
Run:  python tools/make_icon.py   ->  assets/icon.ico and assets/icon-*.png"""

import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "assets")
BASE, MANTLE, RED, MAUVE, TEAL, TEXT = "#1e1e2e", "#11111b", "#f38ba8", "#cba6f7", "#94e2d5", "#cdd6f4"


def draw(size=1024):
    S = size
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # tile with a vertical gradient
    tile = Image.new("RGBA", (S, S))
    px = tile.load()
    top, bot = (0x31, 0x32, 0x44), (0x11, 0x11, 0x1b)
    for y in range(S):
        t = y / (S - 1)
        c = tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)) + (255,)
        for x in range(S):
            px[x, y] = c
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.22), fill=255)
    img.paste(tile, (0, 0), mask)
    d = ImageDraw.Draw(img)
    cx = cy = S // 2
    # sound waves left and right of the dot
    for k, col, w in ((1, MAUVE, 0.035), (2, TEAL, 0.03)):
        r = int(S * (0.20 + 0.105 * k))
        box = (cx - r, cy - r, cx + r, cy + r)
        wd = int(S * w)
        d.arc(box, start=-48, end=48, fill=col, width=wd)
        d.arc(box, start=132, end=228, fill=col, width=wd)
    # the record dot with a glow
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((cx - S * 0.2, cy - S * 0.2, cx + S * 0.2, cy + S * 0.2), fill=RED)
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.05))
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)
    r = int(S * 0.165)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=RED)
    r2 = int(S * 0.058)
    d.ellipse((cx - r2 - int(S * 0.045), cy - r2 - int(S * 0.05), cx + r2 - int(S * 0.045), cy + r2 - int(S * 0.05)),
              fill="#fbd3de")                                         # small highlight
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    big = draw(1024)
    sizes = [16, 20, 24, 32, 48, 64, 128, 256]
    for s in sizes:
        big.resize((s, s), Image.LANCZOS).save(os.path.join(OUT, "icon-%d.png" % s))
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "icon.ico"), sizes=[(s, s) for s in sizes])
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
