"""Bip&Go UGC — sous-titres animés + animations dynamiques.

Usage : python3 render.py <video_source.mp4> <sortie.mp4>
"""
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30

# Charte Bip&Go
LOGO = (0xD4, 0xEE, 0xF4)   # #D4EEF4
TEXTE = (0x0D, 0x38, 0x3F)  # #0D383F

FONT_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FONT_XBOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

END_CARD = 23.667          # début du carton final (pas de zoom ni sous-titres)
CUTS = [0.0, 2.633, 8.533, 12.233, 19.033]
CAPTION_Y = 1130           # centre des sous-titres (hors zone UI Reels du bas)

# (mot, début, fin, emphase)
WORDS = [
    [("QUAND ON", 0.00, 0.28), ("ENCHAÎNE", 0.28, 0.66), ("4-5", 0.66, 1.08, 1)],
    [("RENDEZ-VOUS", 1.08, 1.42), ("CLIENTS", 1.42, 1.58), ("PAR", 1.58, 1.78), ("JOUR", 1.78, 2.00)],
    [("IL", 2.16, 2.20), ("NE", 2.20, 2.24), ("FAUT", 2.24, 2.30), ("SURTOUT", 2.30, 2.62)],
    [("PAS", 2.62, 2.94), ("PERDRE", 2.94, 3.12), ("DE", 3.12, 3.24), ("TEMPS", 3.24, 3.50, 1)],
    [("UN", 3.58, 3.76), ("CLIENT", 3.76, 4.02), ("QUI", 4.02, 4.20), ("ATTEND", 4.20, 4.34)],
    [("TROP", 4.34, 4.56), ("LONGTEMPS", 4.56, 4.95)],
    [("AU", 5.26, 5.46), ("MIEUX", 5.46, 5.66), ("IL", 5.66, 6.12), ("EST", 6.12, 6.24), ("ÉNERVÉ", 6.24, 6.58, 1)],
    [("ET", 6.58, 7.08), ("AU", 7.08, 7.24), ("PIRE", 7.24, 7.52)],
    [("IL", 7.52, 7.92), ("ANNULE", 7.92, 8.30, 1)],
    [("MAIS", 8.54, 8.68), ("DEPUIS", 8.68, 8.90), ("QUE", 8.90, 9.04), ("J'AI", 9.04, 9.14)],
    [("BIP&GO", 9.14, 9.70, 1)],
    [("UN", 9.86, 9.98), ("PETIT", 9.98, 10.12), ("BADGE", 10.12, 10.32)],
    [("COLLÉ", 10.32, 10.68), ("SUR", 10.68, 10.78), ("MON", 10.78, 10.86), ("PARE-BRISE", 10.86, 11.28)],
    [("JE", 11.44, 11.54), ("PASSE", 11.54, 11.70), ("LES", 11.70, 11.88), ("PÉAGES", 11.88, 12.20)],
    [("SANS", 12.20, 12.38), ("M'ARRÊTER", 12.38, 12.90, 1)],
    [("JE", 13.46, 13.82), ("RALENTIS", 13.82, 14.18)],
    [("LA", 14.38, 14.50), ("BARRIÈRE", 14.50, 14.70), ("S'OUVRE", 14.70, 15.14)],
    [("JE", 15.30, 15.38), ("REPARS", 15.38, 15.62), ("DIRECT", 15.62, 16.10, 1)],
    [("SUR", 16.36, 16.52), ("UNE", 16.52, 16.62), ("JOURNÉE", 16.62, 16.78)],
    [("AVEC", 16.78, 16.96), ("PLUSIEURS", 16.96, 17.28), ("TRAJETS", 17.28, 17.66)],
    [("ÇA", 17.80, 17.88), ("CHANGE", 17.88, 18.04), ("VRAIMENT", 18.04, 18.36)],
    [("LA", 18.36, 18.52), ("DONNE", 18.52, 18.85, 1)],
    [("GRÂCE", 19.16, 19.46), ("À", 19.46, 19.58), ("CE", 19.58, 19.66), ("BADGE", 19.66, 19.90)],
    [("J'ENCHAÎNE", 20.18, 20.44), ("PLUS", 20.44, 20.64)],
    [("DE", 20.64, 20.80), ("RENDEZ-VOUS", 20.80, 21.18)],
    [("ET", 21.18, 21.58), ("IL", 21.58, 21.66), ("ME", 21.66, 21.76), ("FAIT", 21.76, 21.86), ("GAGNER", 21.86, 22.04)],
    [("DU", 22.04, 22.18), ("TEMPS", 22.18, 22.36, 1)],
    [("ET", 22.36, 22.70), ("DE", 22.70, 22.80), ("L'ARGENT", 22.80, 23.20, 1)],
]

# Stickers : (début, fin, texte, emoji, x, y, rotation°)
STICKERS = [
    (0.66, 2.55, "4-5 RDV / JOUR", "📅", 540, 430, -4),
    (6.24, 7.45, None, "😤", 830, 860, 8),
    (7.92, 8.50, None, "❌", 830, 860, -6),
    (9.14, 11.30, "LE BADGE TÉLÉPÉAGE", "⚡", 540, 430, 3),
    (12.20, 13.40, "0 ARRÊT AU PÉAGE", "🚗", 540, 430, -3),
    (15.62, 16.30, None, "💨", 820, 870, 6),
    (17.80, 18.95, None, "🔥", 820, 870, -8),
    (22.04, 23.60, "+ DE TEMPS", "⏱️", 540, 380, -4),
    (22.70, 23.60, "+ D'ARGENT", "💶", 540, 590, 4),
]

# Zooms « punch » sur les mots forts
PUNCHES = [w[1] for line in WORDS for w in line if len(w) > 3] + CUTS[1:]


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_back(x, s=2.2):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_out_cubic(x):
    return 1 - (1 - clamp(x)) ** 3


# ---------- rendu des éléments ----------
_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


_emoji_cache = {}


def emoji_img(ch, size):
    key = (ch, size)
    if key not in _emoji_cache:
        f = font(FONT_EMOJI, 109)
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
        im = im.crop(im.getbbox()).resize((size, size), Image.LANCZOS)
        _emoji_cache[key] = im
    return _emoji_cache[key]


def with_shadow(layer, offset=(0, 10), blur=14, alpha=110):
    """Ajoute une ombre portée douce sous un calque RGBA."""
    pad = blur * 3
    out = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    a = layer.split()[3].point(lambda v: v * alpha // 255)
    sh.paste((0, 0, 0, 255), (pad + offset[0], pad + offset[1]), a)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sh)
    out.alpha_composite(layer, (pad, pad))
    return out


def paste_center(frame, layer, cx, cy, scale=1.0, rot=0.0, opacity=1.0):
    if scale <= 0.01 or opacity <= 0.01:
        return
    if scale != 1.0:
        layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))), Image.BICUBIC)
    if rot:
        layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    if opacity < 1.0:
        a = layer.split()[3].point(lambda v: int(v * opacity))
        layer.putalpha(a)
    frame.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


CAP_SIZE = 92
CAP_MAXW = 900


def layout_caption(line):
    """Répartit les mots d'un bloc sur 1 ou 2 lignes."""
    f = font(FONT_BLACK, CAP_SIZE)
    space = f.getlength(" ")
    rows, cur, curw = [], [], 0
    for w in line:
        ww = f.getlength(w[0])
        if cur and curw + space + ww > CAP_MAXW:
            rows.append(cur)
            cur, curw = [], 0
        cur.append(w)
        curw += (space if len(cur) > 1 else 0) + ww
    rows.append(cur)
    return rows


def render_caption(line, t):
    """Bloc de sous-titres ; le mot prononcé est surligné dans une pastille."""
    f = font(FONT_BLACK, CAP_SIZE)
    space = f.getlength(" ") + 4
    rows = layout_caption(line)
    lh = CAP_SIZE + 26
    layer = Image.new("RGBA", (W, lh * len(rows) + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for ri, row in enumerate(rows):
        widths = [f.getlength(w[0]) for w in row]
        total = sum(widths) + space * (len(row) - 1)
        x = (W - total) / 2
        y = 30 + ri * lh + lh / 2
        for w, ww in zip(row, widths):
            active = w[1] <= t < (w[2] if w is not line[-1] else 1e9)
            spoken = t >= w[1]
            if active:
                # pastille qui « pop » à l'activation
                p = ease_out_back((t - w[1]) / 0.12, 3)
                padx, pady = 18 * p, 12 * p
                d.rounded_rectangle(
                    (x - padx, y - CAP_SIZE / 2 - pady, x + ww + padx, y + CAP_SIZE / 2 + pady + 4),
                    radius=22, fill=LOGO + (255,))
                d.text((x, y), w[0], font=f, fill=TEXTE, anchor="lm")
            else:
                fill = LOGO if spoken else (255, 255, 255)
                d.text((x, y), w[0], font=f, fill=fill, anchor="lm",
                       stroke_width=11, stroke_fill=TEXTE)
            x += ww + space
    return with_shadow(layer, (0, 8), 10, 120)


def render_sticker(text, emo):
    """Étiquette arrondie #0D383F, texte #D4EEF4, avec emoji."""
    f = font(FONT_BLACK, 60)
    es = 80
    if text is None:
        im = Image.new("RGBA", (es * 2, es * 2), (0, 0, 0, 0))
        im.alpha_composite(emoji_img(emo, int(es * 1.6)), (int(es * 0.2), int(es * 0.2)))
        return with_shadow(im, (0, 10), 12, 120)
    tw = f.getlength(text)
    pad = 38
    w = int(tw + es + pad * 2 + 24)
    h = 124
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=36, fill=TEXTE + (255,), outline=LOGO + (255,), width=6)
    im.alpha_composite(emoji_img(emo, es), (pad, (h - es) // 2))
    d.text((pad + es + 24, h / 2 + 2), text, font=f, fill=LOGO, anchor="lm")
    return with_shadow(im, (0, 12), 14, 130)


# Pré-rendu des stickers
STICKER_IMGS = [render_sticker(s[2], s[3]) for s in STICKERS]


def zoom_at(t):
    if t >= END_CARD:
        return 1.0
    shot_start = max(c for c in CUTS if c <= t)
    z = 1.0 + 0.012 * (t - shot_start)           # lente poussée continue
    for p in PUNCHES:                              # punch-in sur les temps forts
        if p <= t < p + 0.45:
            k = (t - p) / 0.45
            z += 0.07 * math.sin(math.pi * min(1, k * 2.5)) * (1 - k) + 0.02 * ease_out_cubic(k) * (1 - k)
    return z


def shake_at(t):
    """Petite secousse sur « ANNULE » et « M'ARRÊTER »."""
    for p in (7.92, 12.38):
        if p <= t < p + 0.25:
            a = 14 * (1 - (t - p) / 0.25)
            return a * math.sin(t * 90), a * math.cos(t * 70)
    return 0, 0


def transform(frame, t):
    z = zoom_at(t)
    dx, dy = shake_at(t)
    if z == 1.0 and dx == 0 and dy == 0:
        return frame
    cw, ch = W / z, H / z
    x0 = (W - cw) / 2 + dx / z
    y0 = (H - ch) / 2 + dy / z
    return frame.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC)


def flash_at(t):
    """Flash blanc bref sur chaque cut."""
    for c in CUTS[1:]:
        if c <= t < c + 0.12:
            return 0.35 * (1 - (t - c) / 0.12)
    return 0.0


def current_line(t):
    for i, line in enumerate(WORDS):
        start = line[0][1]
        nxt = WORDS[i + 1][0][1] if i + 1 < len(WORDS) else END_CARD
        end = min(nxt, line[-1][2] + 0.35)
        if start <= t < end:
            return line
    return None


def main():
    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", SRC, "-map", "0:v", "-map", "1:a", "-c:a", "copy",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    fsize = W * H * 3
    n = 0
    cap_cache = {}
    while True:
        buf = dec.stdout.read(fsize)
        if len(buf) < fsize:
            break
        t = n / FPS
        frame = Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1)
        frame = transform(frame, t).convert("RGBA")

        fl = flash_at(t)
        if fl:
            frame = Image.blend(frame, Image.new("RGBA", (W, H), (255, 255, 255, 255)), fl)

        # stickers
        for (s0, s1, _, _, x, y, rot), img in zip(STICKERS, STICKER_IMGS):
            if s0 <= t < s1:
                k_in = (t - s0) / 0.28
                k_out = (s1 - t) / 0.15
                sc = ease_out_back(k_in) * clamp(k_out)
                wob = rot + 3 * math.sin((t - s0) * 6)
                yy = y - 6 * math.sin((t - s0) * 4)
                paste_center(frame, img, x, yy, sc, wob)

        # sous-titres
        line = current_line(t)
        if line is not None:
            active = max((i for i, w in enumerate(line) if w[1] <= t), default=0)
            key = (id(line), active, round(min(t - line[active][1], 0.12) * FPS))
            if key not in cap_cache:
                cap_cache[key] = render_caption(line, t)
            k = (t - line[0][1]) / 0.18
            sc = 0.75 + 0.25 * ease_out_back(k, 2.5)
            emph = any(len(w) > 3 and w[1] <= t < w[2] for w in line)
            if emph:
                sc *= 1.0 + 0.08 * math.sin(math.pi * clamp((t - line[active][1]) / 0.25))
            paste_center(frame, cap_cache[key], W / 2, CAPTION_Y, sc, 0, clamp(k * 2))

        enc.stdin.write(frame.convert("RGB").tobytes())
        n += 1
        if n % 60 == 0:
            print(f"{t:.1f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print("frames:", n)


if __name__ == "__main__":
    main()
