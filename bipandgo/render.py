"""Bip&Go UGC — sous-titres incrustés (.ass), animations dynamiques et bruitages.

Usage : python3 render.py <video_source.mp4> <dossier_polices> <dossier_sortie>

Le dossier de polices doit contenir AvenirNextCyr-Bold.ttf (sous-titres)
et AvenirNextCyr-Heavy.ttf (étiquettes).
Produit : bipandgo_ugc_soustitres.mp4, .ass, .srt et controle_zones.png.
"""
import math
import os
import shutil
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, FONTS_DIR, OUT_DIR = sys.argv[1], sys.argv[2], sys.argv[3]
OUT = os.path.join(OUT_DIR, "bipandgo_ugc_soustitres.mp4")
ASS = os.path.join(OUT_DIR, "bipandgo_ugc_soustitres.ass")
SRT = os.path.join(OUT_DIR, "bipandgo_ugc_soustitres.srt")
W, H, FPS = 1080, 1920, 30

# Charte Bip&Go
LOGO = (0xD4, 0xEE, 0xF4)   # #D4EEF4
TEXTE = (0x0D, 0x38, 0x3F)  # #0D383F

FONT_CAPTION = os.path.join(FONTS_DIR, "AvenirNextCyr-Bold.ttf")
FONT_HEAVY = os.path.join(FONTS_DIR, "AvenirNextCyr-Heavy.ttf")
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

# Zone de sécurité Meta Reels ads
SAFE_TOP, SAFE_BOTTOM, SAFE_SIDE = 269, 1248, 65

# Sous-titres (cf. instructions créatives)
CAP_SIZE = 68
CAP_MARGIN_LR = 90
CAP_MARGIN_V = 720          # bas du texte à ~y 1200
CAP_MAX_CHARS = 29          # cible 25, limite 29

END_CARD = 23.667           # carton final : ni zoom ni sous-titres
CUTS = [0.0, 2.633, 8.533, 12.233, 19.033]

# Mots horodatés (transcription corrigée)
WORDS = [
    ("Quand", 0.00, 0.14), ("t'enchaînes", 0.14, 0.66), ("4-5", 0.66, 1.08),
    ("rendez-vous", 1.08, 1.42), ("clients", 1.42, 1.58), ("par", 1.58, 1.78),
    ("jour,", 1.78, 2.00), ("il", 2.16, 2.20), ("ne", 2.20, 2.24), ("faut", 2.24, 2.30),
    ("surtout", 2.30, 2.62), ("pas", 2.62, 2.94), ("perdre", 2.94, 3.12), ("de", 3.12, 3.24),
    ("temps", 3.24, 3.42),
    ("Un", 3.58, 3.76), ("client", 3.76, 4.02), ("qui", 4.02, 4.20), ("attend", 4.20, 4.34),
    ("trop", 4.34, 4.56), ("longtemps,", 4.56, 4.86), ("au", 5.26, 5.46), ("mieux", 5.46, 5.66),
    ("il", 5.66, 6.12), ("est", 6.12, 6.24), ("énervé,", 6.24, 6.58), ("et", 6.58, 7.08),
    ("au", 7.08, 7.24), ("pire", 7.24, 7.52), ("il", 7.52, 7.92), ("annule", 7.92, 8.26),
    ("Mais", 8.54, 8.68), ("depuis", 8.68, 8.90), ("que", 8.90, 9.04), ("j'ai", 9.04, 9.14),
    ("Bip&Go,", 9.14, 9.48), ("un", 9.86, 9.98), ("petit", 9.98, 10.12), ("badge", 10.12, 10.32),
    ("collé", 10.32, 10.68), ("sur", 10.68, 10.78), ("mon", 10.78, 10.86),
    ("pare-brise,", 10.86, 11.28), ("je", 11.44, 11.54), ("passe", 11.54, 11.70),
    ("les", 11.70, 11.88), ("péages", 11.88, 12.20), ("sans", 12.20, 12.38),
    ("m'arrêter", 12.38, 12.76),
    ("Je", 13.46, 13.82), ("ralentis,", 13.82, 14.18), ("la", 14.38, 14.50),
    ("barrière", 14.50, 14.70), ("s'ouvre,", 14.70, 15.14), ("je", 15.30, 15.38),
    ("repars", 15.38, 15.62), ("direct", 15.62, 15.98),
    ("Sur", 16.36, 16.52), ("une", 16.52, 16.62), ("journée", 16.62, 16.78), ("avec", 16.78, 16.96),
    ("plusieurs", 16.96, 17.28), ("trajets,", 17.28, 17.66), ("ça", 17.80, 17.88),
    ("change", 17.88, 18.04), ("vraiment", 18.04, 18.36), ("la", 18.36, 18.52), ("donne", 18.52, 18.70),
    ("Grâce", 19.16, 19.46), ("à", 19.46, 19.58), ("ce", 19.58, 19.66), ("badge,", 19.66, 19.90),
    ("j'enchaîne", 20.18, 20.44), ("plus", 20.44, 20.64), ("de", 20.64, 20.80),
    ("rendez-vous", 20.80, 21.18), ("et", 21.18, 21.58), ("il", 21.58, 21.66), ("me", 21.66, 21.76),
    ("fait", 21.76, 21.86), ("gagner", 21.86, 22.04), ("du", 22.04, 22.18), ("temps", 22.18, 22.36),
    ("et", 22.36, 22.70), ("de", 22.70, 22.80), ("l'argent", 22.80, 23.06),
]

# Découpage en sous-titres ; « | » = retour à la ligne (groupes de sens)
CHUNKS = [
    "Quand t'enchaînes|4-5 rendez-vous clients",
    "par jour, il ne faut surtout|pas perdre de temps",
    "Un client qui attend|trop longtemps,",
    "au mieux il est énervé,",
    "et au pire il annule",
    "Mais depuis que j'ai|Bip&Go,",
    "un petit badge collé|sur mon pare-brise,",
    "je passe les péages|sans m'arrêter",
    "Je ralentis,|la barrière s'ouvre,",
    "je repars direct",
    "Sur une journée avec|plusieurs trajets,",
    "ça change vraiment|la donne",
    "Grâce à ce badge,",
    "j'enchaîne plus|de rendez-vous",
    "et il me fait gagner|du temps et de l'argent",
]

# Étiquettes animées : (début, fin, texte, emoji, y, rotation°, côté d'entrée)
STICKERS = [
    (0.66, 2.55, "4-5 RDV / JOUR", "📅", 430, -3, -1),
    (9.14, 11.35, "LE BADGE TÉLÉPÉAGE", "⚡", 430, 2, 1),
    (12.20, 13.40, "0 ARRÊT AU PÉAGE", "🚗", 430, -2, -1),
    (21.86, 23.60, "+ DE TEMPS", "⏱️", 400, -3, -1),
    (22.36, 23.60, "+ D'ARGENT", "💶", 600, 3, 1),
]
# Un seul emoji isolé, en ponctuation
EMOJIS = [(6.24, 7.40, "😤", 860, 880, 8)]

# Zooms « punch » sur les mots forts + aux cuts
PUNCHES = [0.66, 3.24, 6.24, 7.92, 9.14, 12.38, 15.62, 18.52, 22.18, 22.80] + CUTS[1:]


# ---------- sous-titres .ass / .srt ----------
def build_chunks():
    """Associe les mots aux sous-titres et calcule les timings."""
    chunks, i = [], 0
    for text in CHUNKS:
        lines = text.split("|")
        assert len(lines) <= 2, text
        for ln in lines:
            assert len(ln) <= CAP_MAX_CHARS, f"ligne trop longue : {ln!r}"
        n = len(text.replace("|", " ").split())
        words = WORDS[i:i + n]
        assert [w[0] for w in words] == text.replace("|", " ").split(), text
        brk = len(lines[0].split())
        chunks.append({"words": words, "brk": brk, "lines": lines})
        i += n
    assert i == len(WORDS)
    for k, c in enumerate(chunks):
        c["start"] = c["words"][0][1]
        nxt = chunks[k + 1]["words"][0][1] if k + 1 < len(chunks) else END_CARD - 0.05
        end = c["words"][-1][2] + 0.4
        if nxt - end < 0.6:          # enchaîner sans trou si le prochain arrive vite
            end = nxt
        c["end"] = min(max(end, c["start"] + 1.0), nxt)
    return chunks


def ass_time(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ass_color(rgb, alpha=0):
    r, g, b = rgb
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def write_subtitles(chunks):
    def col(rgb):
        return "&H%02X%02X%02X&" % rgb[::-1]
    # mot prononcé : couleurs inversées + contour épais (effet pastille), légèrement agrandi
    hi = f"{{\\1c{col(TEXTE)}\\3c{col(LOGO)}\\bord13\\fscx108\\fscy108}}"
    lo = f"{{\\1c{col(LOGO)}\\3c{col(TEXTE)}\\bord5\\fscx100\\fscy100}}"
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Avenir Next Cyr Medium,{CAP_SIZE},{ass_color(LOGO)},{ass_color(LOGO)},{ass_color(TEXTE)},{ass_color((0, 0, 0), 0x80)},-1,0,0,0,100,100,0,0,1,5,2,2,{CAP_MARGIN_LR},{CAP_MARGIN_LR},{CAP_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def pop(i, base):
        """Apparition « pop » du bloc, sur son premier événement uniquement."""
        if i:
            return ""
        a, b = round(base * 0.82), round(base * 1.06)
        return (f"{{\\fscx{a}\\fscy{a}\\t(0,110,\\fscx{b}\\fscy{b})"
                f"\\t(110,190,\\fscx{base}\\fscy{base})}}")

    events, srt = [], []
    for n, c in enumerate(chunks, 1):
        ws = c["words"]
        for i, w in enumerate(ws):
            s = c["start"] if i == 0 else w[1]
            e = ws[i + 1][1] if i + 1 < len(ws) else c["end"]
            parts = []
            for j, x in enumerate(ws):
                tok = f"{hi}{pop(i, 108)}{x[0]}{lo}{pop(i, 100)}" if j == i else x[0]
                parts.append(("\\N" if j == c["brk"] and j > 0 else (" " if j else "")) + tok)
            events.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Sub,,0,0,0,,{pop(i, 100)}{''.join(parts)}")
        srt.append(f"{n}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n" + "\n".join(c["lines"]) + "\n")
    with open(ASS, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(events) + "\n")
    with open(SRT, "w", encoding="utf-8") as f:
        f.write("\n".join(srt))


def report(chunks):
    print("Contrôle des sous-titres :")
    f = ImageFont.truetype(FONT_CAPTION, CAP_SIZE)
    for c in chunks:
        d = c["end"] - c["start"]
        chars = sum(len(ln) for ln in c["lines"])
        width = max(f.getlength(ln) for ln in c["lines"])
        flag = "" if chars / d <= 17 else "  (débit parlé > 17 car/s)"
        assert width <= W - 2 * CAP_MARGIN_LR, f"trop large : {c['lines']}"
        print(f"  {c['start']:5.2f}-{c['end']:5.2f}  {d:.2f}s  {chars / d:4.1f} car/s  "
              f"{int(width)}px  {' / '.join(c['lines'])}{flag}")


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_back(x, s=2.2):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_out_cubic(x):
    return 1 - (1 - clamp(x)) ** 3


# ---------- éléments graphiques ----------
_emoji_cache = {}


def emoji_img(ch, size):
    key = (ch, size)
    if key not in _emoji_cache:
        f = ImageFont.truetype(FONT_EMOJI, 109)
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
        _emoji_cache[key] = im.crop(im.getbbox()).resize((size, size), Image.LANCZOS)
    return _emoji_cache[key]


def with_shadow(layer, offset=(0, 10), blur=14, alpha=110):
    pad = blur * 3
    out = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    a = layer.split()[3].point(lambda v: v * alpha // 255)
    sh.paste((0, 0, 0, 255), (pad + offset[0], pad + offset[1]), a)
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
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
        layer.putalpha(layer.split()[3].point(lambda v: int(v * opacity)))
    frame.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


DEPTH = 12  # épaisseur du bloc « 3D » sous l'étiquette
STICKER_MAXW = W - 2 * SAFE_SIDE - 50  # marge pour la rotation


def sticker_base(text, emo):
    """Étiquette #0D383F, texte #D4EEF4, bloc en relief #D4EEF4."""
    es, pad, gap, h = 92, 40, 26, 150
    size = 72
    while True:  # réduit le corps si l'étiquette déborde de la zone utile
        f = ImageFont.truetype(FONT_HEAVY, size)
        w = int(f.getlength(text) + es + gap + pad * 2)
        if w + DEPTH <= STICKER_MAXW:
            break
        size -= 2
    im = Image.new("RGBA", (w + DEPTH, h + DEPTH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((DEPTH, DEPTH, w + DEPTH - 1, h + DEPTH - 1), radius=34, fill=LOGO + (255,))
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=TEXTE + (255,), outline=LOGO + (255,), width=5)
    im.alpha_composite(emoji_img(emo, es), (pad, (h - es) // 2))
    d.text((pad + es + gap, h / 2 + 4), text, font=f, fill=LOGO, anchor="lm")
    return im, w, h


def shine(base, w, h, k):
    """Reflet lumineux qui balaie l'étiquette (k de 0 à 1)."""
    if not 0 < k < 1:
        return base
    im = base.copy()
    band = Image.new("RGBA", im.size, (0, 0, 0, 0))
    x = -120 + k * (w + 240)
    ImageDraw.Draw(band).polygon([(x, 0), (x + 70, 0), (x + 10, h), (x - 60, h)], fill=(255, 255, 255, 95))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=255)
    band.putalpha(Image.composite(band.split()[3], Image.new("L", im.size, 0), mask))
    im.alpha_composite(band)
    return im


STICKER_BASES = [sticker_base(s[2], s[3]) for s in STICKERS]
for (im, w, h) in STICKER_BASES:
    assert w + DEPTH <= STICKER_MAXW, "étiquette trop large pour la zone utile"


def draw_stickers(frame, t):
    for (s0, s1, _, _, y, rot, side), (base, w, h) in zip(STICKERS, STICKER_BASES):
        if not s0 <= t < s1:
            continue
        a = t - s0
        k_in = ease_out_back(a / 0.38, 1.8)
        k_out = clamp((s1 - t) / 0.18)
        x = W / 2 + side * 320 * (1 - ease_out_cubic(a / 0.38))
        sc = (0.6 + 0.4 * k_in) * (0.7 + 0.3 * k_out)
        # petit battement pour attirer l'œil
        sc *= 1 + 0.035 * math.sin(math.pi * clamp((a - 0.9) / 0.3))
        r = rot * k_in + 1.5 * math.sin(a * 5)
        img = with_shadow(shine(base, w, h, (a - 0.35) / 0.5), (0, 14), 16, 140)
        paste_center(frame, img, x, y - 5 * math.sin(a * 4), sc, r, clamp(a / 0.1) * k_out)
    for s0, s1, ch, x, y, rot in EMOJIS:
        if s0 <= t < s1:
            a = t - s0
            sc = ease_out_back(a / 0.28) * clamp((s1 - t) / 0.15)
            paste_center(frame, with_shadow(emoji_img(ch, 150), (0, 10), 12, 120), x, y, sc,
                         rot + 4 * math.sin(a * 6))


# ---------- mouvements de caméra ----------
def zoom_at(t):
    if t >= END_CARD:
        return 1.0
    shot_start = max(c for c in CUTS if c <= t)
    z = 1.0 + 0.012 * (t - shot_start)
    for p in PUNCHES:
        if p <= t < p + 0.45:
            k = (t - p) / 0.45
            z += 0.07 * math.sin(math.pi * min(1, k * 2.5)) * (1 - k) + 0.02 * ease_out_cubic(k) * (1 - k)
    return z


def shake_at(t):
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
    x0, y0 = (W - cw) / 2 + dx / z, (H - ch) / 2 + dy / z
    return frame.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC)


def flash_at(t):
    for c in CUTS[1:]:
        if c <= t < c + 0.12:
            return 0.35 * (1 - (t - c) / 0.12)
    return 0.0


# ---------- bruitages (synthétisés, libres de droits) ----------
SR = 44100
SFX = os.path.join(OUT_DIR, ".sfx.wav")


def _env(n, attack, decay_pow=3.0):
    t = np.linspace(0, 1, n)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * (1 - t) ** decay_pow


def _lowpass(x, alpha):
    """Filtre passe-bas à un pôle ; alpha peut varier dans le temps."""
    y = np.empty_like(x)
    acc = 0.0
    alpha = np.broadcast_to(alpha, x.shape)
    for i in range(len(x)):
        acc += alpha[i] * (x[i] - acc)
        y[i] = acc
    return y


def sfx_whoosh(dur=0.35):
    n = int(SR * dur)
    rng = np.random.default_rng(int(dur * 1000))
    noise = rng.standard_normal(n)
    sweep = np.linspace(0.02, 0.35, n) ** 1.5          # le filtre s'ouvre : effet « souffle »
    hi = _lowpass(noise, sweep)
    band = hi - _lowpass(hi, 0.01)
    t = np.linspace(0, 1, n)
    env = np.sin(np.pi * t ** 0.7) ** 2
    return band * env / (np.abs(band).max() + 1e-9)


def sfx_pop(f0=520, dur=0.09):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = f0 * (1 + 1.6 * np.exp(-t * 60))               # glissando descendant rapide
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.03, 4)


def sfx_ding(f0=1760, dur=0.6):
    n = int(SR * dur)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f0 * k * t) for k, a in ((1, 1), (2.76, 0.35), (5.4, 0.12)))
    return s * np.exp(-t * 7) * np.clip(t / 0.003, 0, 1) / 1.5


def sfx_impact(dur=0.35):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 55 + 110 * np.exp(-t * 25)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)
    click = np.random.default_rng(7).standard_normal(n) * np.exp(-t * 120) * 0.4
    return np.tanh(1.8 * (body + click)) / np.tanh(1.8)


def build_sfx(duration):
    track = np.zeros(int(SR * (duration + 1)))

    def add(sig, t, gain_db):
        i = int(t * SR)
        sig = sig * 10 ** (gain_db / 20)
        track[i:i + len(sig)] += sig[:len(track) - i]

    for c in CUTS[1:] + [END_CARD]:                    # transitions
        add(sfx_whoosh(0.35), c - 0.2, -11)
    for s0, *_ in STICKERS:                            # étiquettes : souffle + pop + reflet
        add(sfx_whoosh(0.25), s0 - 0.05, -13)
        add(sfx_pop(560), s0 + 0.22, -7)
        add(sfx_ding(2350, 0.35), s0 + 0.4, -21)
    for s0, *_ in EMOJIS:
        add(sfx_pop(700), s0 + 0.12, -9)
    for p in (7.92, 12.38):                            # secousses
        add(sfx_impact(), p, -6)
    add(sfx_ding(1568, 0.9), 26.08, -12)               # « 6 mois offerts »
    add(sfx_ding(2093, 0.9), 26.16, -15)

    pcm = (np.clip(track, -1, 1) * 32767).astype(np.int16)
    with wave.open(SFX, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------- rendu ----------
def ass_fonts_dir():
    """libass : n'exposer que la graisse Bold pour éviter un mauvais appariement."""
    d = os.path.join(OUT_DIR, ".ass_fonts")
    os.makedirs(d, exist_ok=True)
    shutil.copy(FONT_CAPTION, d)
    return d


def control_image():
    """Images de contrôle avec zones interdites Meta en rouge."""
    times = [1.0, 2.5, 9.6, 12.6, 22.9]
    red = "drawbox=x=0:y=0:w=iw:h={t}:color=red@0.35:t=fill," \
          "drawbox=x=0:y={b}:w=iw:h=ih-{b}:color=red@0.35:t=fill," \
          "drawbox=x=0:y=0:w={s}:h=ih:color=red@0.35:t=fill," \
          "drawbox=x=iw-{s}:y=0:w={s}:h=ih:color=red@0.35:t=fill," \
          "drawbox=x=0:y=1200:w=iw:h=2:color=yellow@0.9:t=fill"
    red = red.format(t=SAFE_TOP, b=SAFE_BOTTOM, s=SAFE_SIDE)
    tiles = []
    for i, t in enumerate(times):
        p = os.path.join(OUT_DIR, f".ctrl_{i}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", OUT, "-frames:v", "1",
                        "-vf", red + ",scale=432:-1", p], check=True)
        tiles.append(Image.open(p).convert("RGB"))
        os.remove(p)
    sheet = Image.new("RGB", (432 * len(tiles), tiles[0].height), "white")
    for i, im in enumerate(tiles):
        sheet.paste(im, (432 * i, 0))
    sheet.save(os.path.join(OUT_DIR, "controle_zones.png"))


def main():
    chunks = build_chunks()
    report(chunks)
    write_subtitles(chunks)
    fonts = ass_fonts_dir()
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", SRC], capture_output=True, text=True).stdout)
    build_sfx(dur)

    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", SRC, "-i", SFX,
         "-filter_complex", "[2:a]aformat=channel_layouts=stereo[s];"
                            "[1:a][s]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
         "-map", "0:v", "-map", "[a]", "-c:a", "aac", "-b:a", "256k",
         "-vf", f"ass={ASS}:fontsdir={fonts}",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    fsize = W * H * 3
    n = 0
    while True:
        buf = dec.stdout.read(fsize)
        if len(buf) < fsize:
            break
        t = n / FPS
        frame = transform(Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1), t).convert("RGBA")
        fl = flash_at(t)
        if fl:
            frame = Image.blend(frame, Image.new("RGBA", (W, H), (255, 255, 255, 255)), fl)
        draw_stickers(frame, t)
        enc.stdin.write(frame.convert("RGB").tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    dec.wait()
    shutil.rmtree(fonts)
    os.remove(SFX)
    control_image()
    print("frames:", n)


if __name__ == "__main__":
    main()
