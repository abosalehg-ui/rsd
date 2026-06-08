#!/usr/bin/env python3
"""
رصد (Rasad) — مولّد الأيقونة

يرسم شعار "الرادار" (نفس طابع الواجهة: خلفية داكنة متدرّجة، حلقات سماوية،
مكنسة رادار، ونقطة حمراء نابضة في المركز) ويصدّره كـ:
  - packaging/rasad.ico            (متعدد الأحجام: 16..256) — لـ PyInstaller و Inno Setup
  - frontend/public/favicon.ico    (نفس الأيقونة) — أيقونة تبويب المتصفح
  - packaging/rasad-icon-preview.png (معاينة 256px)

التشغيل:  python packaging/make_icon.py
المتطلّب: pip install pillow
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "packaging"
PUBLIC = ROOT / "frontend" / "public"

# لوحة الألوان (مطابقة لثيم الواجهة)
CYAN = (34, 211, 238)      # #22d3ee
RED = (239, 68, 68)        # #ef4444
BG_INNER = (14, 58, 95)    # #0e3a5f
BG_OUTER = (10, 14, 23)    # #0a0e17

M = 1024                   # دقّة الرسم العالية (تُصغَّر لاحقاً للنعومة)
SIZES = [256, 128, 64, 48, 32, 16]


def radial_gradient(size: int, inner: tuple, outer: tuple, cx: float, cy: float, radius: float) -> Image.Image:
    """تدرّج شعاعي يُرسم بدقّة منخفضة ثم يُكبَّر (سريع وناعم)."""
    s = 200
    g = Image.new("RGB", (s, s))
    px = g.load()
    for y in range(s):
        for x in range(s):
            d = min(1.0, math.hypot(x - cx * s / size, y - cy * s / size) / (radius * s / size))
            px[x, y] = (
                int(inner[0] + (outer[0] - inner[0]) * d),
                int(inner[1] + (outer[1] - inner[1]) * d),
                int(inner[2] + (outer[2] - inner[2]) * d),
            )
    return g.resize((size, size), Image.BICUBIC)


def make_master() -> Image.Image:
    c = M / 2
    img = Image.new("RGBA", (M, M), (0, 0, 0, 0))

    # خلفية متدرّجة داخل مربّع بزوايا دائرية (أيقونة عصرية)
    grad = radial_gradient(M, BG_INNER, BG_OUTER, c, M * 0.40, M * 0.62).convert("RGBA")
    mask = Image.new("L", (M, M), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, M - 1, M - 1], radius=int(M * 0.22), fill=255)
    img.paste(grad, (0, 0), mask)

    overlay = Image.new("RGBA", (M, M), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    # توهّج خلفي ناعم خلف المركز
    glow = Image.new("RGBA", (M, M), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [c - M * 0.34, c - M * 0.34, c + M * 0.34, c + M * 0.34],
        fill=CYAN + (38,),
    )
    overlay = Image.alpha_composite(overlay, glow.filter(ImageFilter.GaussianBlur(M * 0.06)))
    d = ImageDraw.Draw(overlay)

    # مكنسة الرادار: قطاع دائري سماوي خافت يتلاشى
    sweep = Image.new("RGBA", (M, M), (0, 0, 0, 0))
    ImageDraw.Draw(sweep).pieslice(
        [c - M * 0.30, c - M * 0.30, c + M * 0.30, c + M * 0.30],
        start=-95, end=-35, fill=CYAN + (70,),
    )
    overlay = Image.alpha_composite(overlay, sweep.filter(ImageFilter.GaussianBlur(M * 0.012)))
    d = ImageDraw.Draw(overlay)

    # حلقات متّحدة المركز
    for rel, w, a in [(0.30, 7, 200), (0.225, 4, 120), (0.15, 3, 90)]:
        r = M * rel
        d.ellipse([c - r, c - r, c + r, c + r], outline=CYAN + (a,), width=int(w))

    # خطّا التهديف (أفقي/عمودي) خافتان
    rr = M * 0.30
    d.line([c - rr, c, c + rr, c], fill=CYAN + (55,), width=3)
    d.line([c, c - rr, c, c + rr], fill=CYAN + (55,), width=3)

    # نقطة اتصال ساطعة على إحدى الحلقات
    bx, by = c + M * 0.225 * math.cos(math.radians(-65)), c + M * 0.225 * math.sin(math.radians(-65))
    d.ellipse([bx - M * 0.022, by - M * 0.022, bx + M * 0.022, by + M * 0.022], fill=CYAN + (255,))

    # حلقة حمراء + نقطة مركزية (الوميض)
    d.ellipse([c - M * 0.085, c - M * 0.085, c + M * 0.085, c + M * 0.085], outline=RED + (170,), width=5)
    d.ellipse([c - M * 0.042, c - M * 0.042, c + M * 0.042, c + M * 0.042], fill=RED + (255,))

    overlay.putalpha(Image.composite(overlay.getchannel("A"), Image.new("L", (M, M), 0), mask))
    img = Image.alpha_composite(img, overlay)

    # حدّ سماوي رفيع حول الأيقونة
    border = Image.new("RGBA", (M, M), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        [4, 4, M - 5, M - 5], radius=int(M * 0.22), outline=CYAN + (90,), width=6
    )
    img = Image.alpha_composite(img, border)
    return img


def main() -> None:
    master = make_master()
    base = master.resize((256, 256), Image.LANCZOS)

    PKG.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)

    ico_sizes = [(s, s) for s in SIZES]
    base.save(PKG / "rasad.ico", format="ICO", sizes=ico_sizes)
    base.save(PUBLIC / "favicon.ico", format="ICO", sizes=ico_sizes)
    base.save(PKG / "rasad-icon-preview.png", format="PNG")

    print("✅ تم توليد:")
    print("   - packaging/rasad.ico")
    print("   - frontend/public/favicon.ico")
    print("   - packaging/rasad-icon-preview.png")


if __name__ == "__main__":
    main()
