#!/usr/bin/env python3
"""Generate SKJ OS EZ artwork (logo, wallpaper, boot splash, installer images).

Text is converted to outlines with fontTools, so the SVGs don't depend on
installed fonts. PNGs are rendered with ImageMagick (librsvg delegate).

Usage: python3 artwork/generate.py   (needs: fonttools, ImageMagick with RSVG)
Output: packaging/skj-logos/assets/
"""
import subprocess
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "packaging" / "skj-logos" / "assets"
FONT = Path("/usr/share/fonts/aajohan-comfortaa-fonts/Comfortaa-Bold.otf")

# Brand palette
BLUE = "#2563eb"
TEAL = "#14b8a6"
NIGHT = "#0b1020"
NIGHT2 = "#0d2b3e"
WHITE = "#ffffff"
INK = "#0f172a"

font = TTFont(FONT)
glyphset = font.getGlyphSet()
cmap = font.getBestCmap()
upm = font["head"].unitsPerEm
hmtx = font["hmtx"]


def text_path(text, size, x=0.0, baseline=0.0, tracking=0.0):
    """Return (svg path d, (xmin, ymin, xmax, ymax)) for text at given size."""
    scale = size / upm
    pen = SVGPathPen(glyphset)
    bpen = BoundsPen(glyphset)
    cursor = 0.0
    for ch in text:
        gname = cmap[ord(ch)]
        t = (scale, 0, 0, -scale, x + cursor * scale, baseline)
        glyphset[gname].draw(TransformPen(pen, t))
        glyphset[gname].draw(TransformPen(bpen, t))
        cursor += hmtx[gname][0] + tracking * upm
    return pen.getCommands(), bpen.bounds


def centered_text(text, size, cx, cy, tracking=0.0):
    """Path for text whose ink box is centred on (cx, cy)."""
    _, (x0, y0, x1, y1) = text_path(text, size, tracking=tracking)
    dx = cx - (x0 + x1) / 2
    dy = cy - (y0 + y1) / 2
    d, _ = text_path(text, size, x=dx, baseline=dy, tracking=tracking)
    return d


def fit_size(text, width, tracking=0.0):
    _, (x0, _, x1, _) = text_path(text, 100, tracking=tracking)
    return 100 * width / (x1 - x0)


def svg(w, h, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}"><defs>{defs}</defs>{body}</svg>\n')


GRAD = (f'<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{TEAL}"/>'
        f'</linearGradient>')


def mark_body(x, y, s):
    """Rounded-square logo mark with 'SKJ' at (x, y), size s."""
    size = fit_size("SKJ", s * 0.66)
    d = centered_text("SKJ", size, x + s / 2, y + s / 2)
    return (f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{s * 0.22}" fill="url(#g)"/>'
            f'<path d="{d}" fill="{WHITE}"/>')


def logo_mark():
    return svg(512, 512, mark_body(0, 0, 512), GRAD)


def logo_mark_mono(color):
    """Single-colour mark: outlined square, letters knocked out."""
    s = 512
    size = fit_size("SKJ", s * 0.66)
    d = centered_text("SKJ", size, s / 2, s / 2)
    body = (f'<path fill-rule="evenodd" fill="{color}" d="M{s*0.22},0 H{s*0.78} '
            f'A{s*0.22},{s*0.22} 0 0 1 {s},{s*0.22} V{s*0.78} A{s*0.22},{s*0.22} 0 0 1 {s*0.78},{s} '
            f'H{s*0.22} A{s*0.22},{s*0.22} 0 0 1 0,{s*0.78} V{s*0.22} A{s*0.22},{s*0.22} 0 0 1 {s*0.22},0 Z {d}"/>')
    return svg(s, s, body)


def wordmark(color, w=1040, h=320):
    """Horizontal logo: mark + 'SKJ OS EZ'."""
    m = h
    size = fit_size("SKJ OS EZ", w - m - h * 0.18)
    _, (x0, y0, x1, y1) = text_path("SKJ OS EZ", size)
    tx = m + h * 0.18 - x0
    ty = h / 2 - (y0 + y1) / 2
    d, _ = text_path("SKJ OS EZ", size, x=tx, baseline=ty)
    return svg(w, h, mark_body(0, 0, m) + f'<path d="{d}" fill="{color}"/>', GRAD)


def stacked(color, w=600, h=420):
    """Mark above 'SKJ OS EZ' (boot splash, installer)."""
    m = h * 0.62
    size = fit_size("SKJ OS EZ", w * 0.92)
    tsize = min(size, h * 0.2)
    d = centered_text("SKJ OS EZ", tsize, w / 2, m + (h - m) / 2 + h * 0.02)
    return svg(w, h, mark_body((w - m) / 2, 0, m) + f'<path d="{d}" fill="{color}"/>', GRAD)


def wallpaper(w, h):
    defs = (
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{NIGHT}"/><stop offset="1" stop-color="{NIGHT2}"/></linearGradient>'
        f'<radialGradient id="b1"><stop offset="0" stop-color="{BLUE}" stop-opacity=".55"/>'
        f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="b2"><stop offset="0" stop-color="{TEAL}" stop-opacity=".45"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>' + GRAD)
    s = min(w, h) * 0.17
    size = fit_size("SKJ OS EZ", s * 2.2)
    d = centered_text("SKJ OS EZ", size, w / 2, h / 2 + s * 0.78)
    body = (f'<rect width="{w}" height="{h}" fill="url(#bg)"/>'
            f'<circle cx="{w*0.78}" cy="{h*0.25}" r="{w*0.32}" fill="url(#b1)"/>'
            f'<circle cx="{w*0.2}" cy="{h*0.82}" r="{w*0.34}" fill="url(#b2)"/>'
            f'<g opacity=".92">{mark_body(w/2 - s/2, h/2 - s*0.72, s)}</g>'
            f'<path d="{d}" fill="{WHITE}" opacity=".85"/>')
    return svg(w, h, body, defs)


def solid(w, h, color):
    return svg(w, h, f'<rect width="{w}" height="{h}" fill="{color}"/>')


def sidebar_bg(w=406, h=767):
    defs = (f'<linearGradient id="s" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{TEAL}"/></linearGradient>')
    return svg(w, h, f'<rect width="{w}" height="{h}" fill="url(#s)"/>', defs)


def topbar_bg(w=1040, h=132):
    defs = (f'<linearGradient id="t" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{TEAL}"/></linearGradient>')
    return svg(w, h, f'<rect width="{w}" height="{h}" fill="url(#t)"/>', defs)


def write(name, content):
    p = OUT / "svg" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def render(src, dest, w, h=None):
    dest = OUT / dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    geom = f"{w}x{h}" if h else f"{w}x{w}"
    subprocess.run(["magick", "-background", "none", "-density", "384", f"RSVG:{src}",
                    "-resize", geom, "-gravity", "center", "-extent", geom,
                    "-strip", f"PNG32:{dest}"], check=True)


def main():
    mark = write("skj-logo-mark.svg", logo_mark())
    mono_w = write("skj-logo-mark-white.svg", logo_mark_mono(WHITE))
    mono_s = write("skj-logo-mark-symbolic.svg", logo_mark_mono("#bebebe"))
    wm_light = write("skj-wordmark-darkbg.svg", wordmark(WHITE))   # for dark backgrounds
    wm_dark = write("skj-wordmark-lightbg.svg", wordmark(INK))     # for light backgrounds
    st_white = write("skj-stacked-white.svg", stacked(WHITE))
    wp = write("wallpaper-3840x2160.svg", wallpaper(3840, 2160))
    wp_v = write("wallpaper-1080x1920.svg", wallpaper(1080, 1920))
    sb = write("anaconda-sidebar-bg.svg", sidebar_bg())
    tb = write("anaconda-topbar-bg.svg", topbar_bg())

    for s in (16, 22, 24, 32, 36, 48, 64, 96, 128, 256, 512):
        render(mark, f"icons/{s}/skj-logo-icon.png", s)
    render(mono_w, "system-logo-white.png", 252)
    render(mark, "logo-sprite.png", 252)
    render(mark, "bootlogo_128.png", 128)
    render(mark, "bootlogo_256.png", 256)
    render(mark, "favicon.png", 16)
    render(wm_dark, "logo.png", 521, 164)
    render(wm_dark, "logo-small.png", 150, 47)
    render(wm_dark, "logo-med.png", 279, 80)
    render(wm_light, "whitelogo-med.png", 279, 80)
    render(wm_light, "gdm-logo.png", 149, 43)
    render(st_white, "plymouth-watermark.png", 360, 252)
    render(st_white, "anaconda-sidebar-logo.png", 150, 105)
    render(wm_light, "anaconda-header.png", 119, 36)
    render(sb, "anaconda-sidebar-bg.png", 406, 767)
    render(tb, "anaconda-topbar-bg.png", 1040, 132)
    render(wp, "wallpaper/3840x2160.png", 3840, 2160)
    render(wp, "wallpaper/1920x1080.png", 1920, 1080)
    render(wp_v, "wallpaper/1080x1920.png", 1080, 1920)
    render(wp, "wallpaper/screenshot.png", 400, 225)
    print(f"artwork written to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
