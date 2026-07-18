import colorsys
import math
import os
import struct
import zlib


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PNG_PATH = os.path.join(ROOT, "app_icon.png")
ICO_PATH = os.path.join(ROOT, "app_icon.ico")


def clamp(value, low, high):
    return max(low, min(high, value))


def mix(a, b, amount):
    return tuple(int(round(a[i] * (1 - amount) + b[i] * amount)) for i in range(4))


def rounded_rect_alpha(x, y, radius):
    edge = 1 - radius
    ax = abs(x)
    ay = abs(y)
    if ax <= edge and ay <= 1:
        return 1
    if ay <= edge and ax <= 1:
        return 1
    dx = ax - edge
    dy = ay - edge
    distance = math.sqrt(max(dx, 0) ** 2 + max(dy, 0) ** 2)
    return clamp((radius - distance) * 140, 0, 1)


def pixel_at(x, y):
    bg_alpha = rounded_rect_alpha(x, y, 0.24)
    if bg_alpha <= 0:
        return 0, 0, 0, 0

    top = (41, 45, 49, 255)
    bottom = (22, 24, 27, 255)
    bg = mix(top, bottom, (y + 1) / 2)
    bg = mix(bg, (0, 201, 80, 255), clamp((x + y + 1.0) * 0.08, 0, 0.12))

    distance = math.sqrt(x * x + y * y)
    angle = (math.atan2(y, x) + math.pi) / (2 * math.pi)
    ring_outer = 0.57
    ring_inner = 0.35
    ring_edge = 0.018

    ring_alpha = clamp((ring_outer - distance) / ring_edge, 0, 1) * clamp(
        (distance - ring_inner) / ring_edge, 0, 1
    )
    if ring_alpha:
        r, g, b = colorsys.hsv_to_rgb(angle, 0.92, 0.98)
        ring = (int(r * 255), int(g * 255), int(b * 255), 255)
        bg = mix(bg, ring, ring_alpha)

    inner_alpha = clamp((0.31 - distance) / 0.02, 0, 1)
    if inner_alpha:
        bg = mix(bg, (238, 244, 249, 255), inner_alpha)

    lens_alpha = clamp((0.24 - distance) / 0.02, 0, 1)
    if lens_alpha:
        bg = mix(bg, (27, 31, 35, 255), lens_alpha)

    line_alpha = 0
    if abs(x) < 0.018 and abs(y) < 0.22:
        line_alpha = 0.75
    if abs(y) < 0.018 and abs(x) < 0.22:
        line_alpha = max(line_alpha, 0.75)
    if line_alpha:
        bg = mix(bg, (238, 244, 249, 255), line_alpha)

    dot_x = x - 0.30
    dot_y = y - 0.28
    dot_d = math.sqrt(dot_x * dot_x + dot_y * dot_y)
    outline = clamp((0.16 - dot_d) / 0.018, 0, 1)
    fill = clamp((0.12 - dot_d) / 0.018, 0, 1)
    if outline:
        bg = mix(bg, (238, 244, 249, 255), outline)
    if fill:
        bg = mix(bg, (0, 201, 80, 255), fill)

    return bg[0], bg[1], bg[2], int(round(bg[3] * bg_alpha))


def render(size):
    scale = 3
    data = bytearray()
    for py in range(size):
        for px in range(size):
            total = [0, 0, 0, 0]
            for sy in range(scale):
                for sx in range(scale):
                    x = ((px + (sx + 0.5) / scale) / size) * 2 - 1
                    y = ((py + (sy + 0.5) / scale) / size) * 2 - 1
                    rgba = pixel_at(x, y)
                    for channel in range(4):
                        total[channel] += rgba[channel]
            samples = scale * scale
            data.extend(int(round(value / samples)) for value in total)
    return bytes(data)


def png_bytes(width, height, rgba):
    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw.extend(rgba[y * stride : (y + 1) * stride])

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def write_ico(images):
    entries = []
    payload = bytearray()
    offset = 6 + len(images) * 16
    for size, image in images:
        png = png_bytes(size, size, image)
        width_byte = 0 if size == 256 else size
        entries.append((width_byte, width_byte, len(png), offset))
        payload.extend(png)
        offset += len(png)

    with open(ICO_PATH, "wb") as file:
        file.write(struct.pack("<HHH", 0, 1, len(entries)))
        for width, height, length, item_offset in entries:
            file.write(struct.pack("<BBBBHHII", width, height, 0, 0, 1, 32, length, item_offset))
        file.write(payload)


def main():
    images = [(size, render(size)) for size in (16, 24, 32, 48, 64, 128, 256)]
    write_ico(images)
    with open(PNG_PATH, "wb") as file:
        file.write(png_bytes(256, 256, images[-1][1]))
    print(ICO_PATH)
    print(PNG_PATH)


if __name__ == "__main__":
    main()
