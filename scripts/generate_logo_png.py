#!/usr/bin/env python3
"""Generates a 256x256 RGBA PNG version of assets/logo.svg for the VS Code Marketplace.

Microsoft's Visual Studio Marketplace requires a PNG icon (>= 128x128) in package.json
and explicitly rejects SVG icons. This script renders the exact geometry of assets/logo.svg
with 2x supersampled anti-aliasing using only the Python standard library.
"""

from __future__ import annotations

import math
from pathlib import Path
import struct
import zlib
from typing import Tuple

Color = Tuple[float, float, float, float]  # r, g, b (0-255), a (0.0-1.0)


def hex_to_rgba(hex_str: str, alpha: float = 1.0) -> Color:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def lerp_color(c1: Color, c2: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
        c1[3] + (c2[3] - c1[3]) * t,
    )


def blend(dst: Color, src: Color) -> Color:
    sa = src[3]
    if sa <= 0.0:
        return dst
    if sa >= 1.0:
        return src
    da = dst[3]
    out_a = sa + da * (1.0 - sa)
    if out_a <= 1e-6:
        return (0.0, 0.0, 0.0, 0.0)
    out_r = (src[0] * sa + dst[0] * da * (1.0 - sa)) / out_a
    out_g = (src[1] * sa + dst[1] * da * (1.0 - sa)) / out_a
    out_b = (src[2] * sa + dst[2] * da * (1.0 - sa)) / out_a
    return (out_r, out_g, out_b, out_a)


def dist_to_segment(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
    dx = x2 - x1
    dy = y2 - y1
    len_sq = dx * dx + dy * dy
    if len_sq <= 1e-9:
        return math.hypot(px - x1, py - y1), 0.0
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y), t


def point_in_triangle(px: float, py: float, ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
    d1 = (px - bx) * (ay - by) - (ax - bx) * (py - by)
    d2 = (px - cx) * (by - cy) - (bx - cx) * (py - cy)
    d3 = (px - ax) * (cy - ay) - (cx - ax) * (py - ay)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def prism_gradient(px: float, py: float, is_stroke: bool) -> Color:
    # Linear gradient from (64, 44) to (192, 212)
    gx, gy = 192.0 - 64.0, 212.0 - 44.0
    t = ((px - 64.0) * gx + (py - 44.0) * gy) / (gx * gx + gy * gy)
    t = max(0.0, min(1.0, t))
    if is_stroke:
        c0 = hex_to_rgba("#38BDF8", 1.0)
        c1 = hex_to_rgba("#818CF8", 1.0)
        c2 = hex_to_rgba("#E879F9", 1.0)
    else:
        c0 = hex_to_rgba("#38BDF8", 0.28)
        c1 = hex_to_rgba("#818CF8", 0.18)
        c2 = hex_to_rgba("#C084FC", 0.28)
    if t < 0.5:
        return lerp_color(c0, c1, t * 2.0)
    return lerp_color(c1, c2, (t - 0.5) * 2.0)


def sample_pixel(px: float, py: float) -> Color:
    out: Color = (0.0, 0.0, 0.0, 0.0)

    # Subtle dark rounded badge backdrop so the icon pops on both light and dark Marketplace themes
    cx, cy = 128.0, 128.0
    rx = max(0.0, abs(px - cx) - (112.0 - 28.0))
    ry = max(0.0, abs(py - cy) - (112.0 - 28.0))
    corner_dist = math.hypot(rx, ry) - 28.0
    if corner_dist < 1.0:
        alpha = max(0.0, min(1.0, 0.5 - corner_dist)) * 0.92
        bg_t = (px + py) / 512.0
        bg_col = lerp_color(hex_to_rgba("#0F172A", alpha), hex_to_rgba("#1E1B4B", alpha), bg_t)
        out = blend(out, bg_col)

    # 1. Incoming diffuse prompt ray: (26,148) -> (96,128)
    d_in, _ = dist_to_segment(px, py, 26.0, 148.0, 96.0, 128.0)
    if d_in < 3.0:
        cov = max(0.0, min(1.0, 2.5 - d_in))
        out = blend(out, hex_to_rgba("#F8FAFC", cov))

    # 2. Internal refraction beam polygon: (96,128), (158,104), (166,144)
    if point_in_triangle(px, py, 96.0, 128.0, 158.0, 104.0, 166.0, 144.0):
        out = blend(out, hex_to_rgba("#38BDF8", 0.35))

    d_mid, _ = dist_to_segment(px, py, 96.0, 128.0, 162.0, 122.0)
    if d_mid < 2.5:
        cov = max(0.0, min(1.0, 2.0 - d_mid))
        out = blend(out, hex_to_rgba("#E0F2FE", cov))

    # 3. Three Refracted Output Spectrums
    rays = [
        (158.0, 106.0, 230.0, 74.0, "#F59E0B", "#FBBF24"),   # Precision (Amber)
        (162.0, 124.0, 232.0, 124.0, "#06B6D4", "#22D3EE"),  # Root-Cause (Cyan)
        (166.0, 142.0, 230.0, 174.0, "#10B981", "#34D399"),  # Strict Spec (Emerald)
    ]
    for x1, y1, x2, y2, line_hex, dot_hex in rays:
        d_ray, _ = dist_to_segment(px, py, x1, y1, x2, y2)
        if d_ray < 3.8:
            cov = max(0.0, min(1.0, 3.3 - d_ray))
            out = blend(out, hex_to_rgba(line_hex, cov))
        d_dot = math.hypot(px - x2, py - y2)
        if d_dot < 5.0:
            cov = max(0.0, min(1.0, 4.5 - d_dot))
            out = blend(out, hex_to_rgba(dot_hex, cov))

    # 4. Central Prism Fill: (124,44), (56,204), (192,204)
    if point_in_triangle(px, py, 124.0, 44.0, 56.0, 204.0, 192.0, 204.0):
        out = blend(out, prism_gradient(px, py, is_stroke=False))

    # 5. Subtle inner prism facet: (124,44) -> (124,204) dashed
    d_facet, t_facet = dist_to_segment(px, py, 124.0, 44.0, 124.0, 204.0)
    if d_facet < 1.8 and int(t_facet * 160.0) % 10 < 5:
        cov = max(0.0, min(1.0, 1.3 - d_facet)) * 0.4
        out = blend(out, hex_to_rgba("#818CF8", cov))

    # 6. Central Prism Stroke (3 edges)
    edges = [
        (124.0, 44.0, 56.0, 204.0),
        (56.0, 204.0, 192.0, 204.0),
        (192.0, 204.0, 124.0, 44.0),
    ]
    d_edge = min(dist_to_segment(px, py, ax, ay, bx, by)[0] for ax, ay, bx, by in edges)
    if d_edge < 4.2:
        cov = max(0.0, min(1.0, 3.8 - d_edge))
        stroke_col = prism_gradient(px, py, is_stroke=True)
        out = blend(out, (stroke_col[0], stroke_col[1], stroke_col[2], cov))

    return out


def write_png(path: Path, width: int = 256, height: int = 256) -> None:
    raw_rows = bytearray()
    offsets = (0.25, 0.75)
    for y in range(height):
        raw_rows.append(0)  # Filter type 0 (None)
        for x in range(width):
            r_sum = g_sum = b_sum = a_sum = 0.0
            for oy in offsets:
                for ox in offsets:
                    c = sample_pixel(x + ox, y + oy)
                    r_sum += c[0]
                    g_sum += c[1]
                    b_sum += c[2]
                    a_sum += c[3]
            r = int(round(max(0.0, min(255.0, r_sum / 4.0))))
            g = int(round(max(0.0, min(255.0, g_sum / 4.0))))
            b = int(round(max(0.0, min(255.0, b_sum / 4.0))))
            a = int(round(max(0.0, min(255.0, (a_sum / 4.0) * 255.0))))
            raw_rows.extend((r, g, b, a))

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    idat = zlib.compress(bytes(raw_rows), level=9)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", idat)
        + make_chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes)


if __name__ == "__main__":
    out_file = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
    write_png(out_file)
    print(f"Generated {out_file} ({out_file.stat().st_size} bytes)")
