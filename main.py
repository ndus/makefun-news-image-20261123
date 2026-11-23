"""Small standard-library renderer for a deterministic newspaper PNG."""

import os
import struct
import zlib


WIDTH = 1000
HEIGHT = 1000
MAX_PNG_BYTES = 1024 * 1024

PAPER = (247, 243, 233)
INK = (24, 24, 28)
ACCENT_RED = (164, 32, 28)
MUTED_GREY = (96, 96, 100)
PANEL_TINT = (238, 231, 216)
HAIRLINE = (170, 160, 140)

# A tightly packed RGB buffer, initialized to the newspaper paper color.
buffer = bytearray(bytes(PAPER) * (WIDTH * HEIGHT))


def set_pixel(x, y, color):
    """Set one pixel when it falls inside the canvas."""
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        offset = (y * WIDTH + x) * 3
        buffer[offset:offset + 3] = bytes(color)


def fill_rect(x, y, width, height, color):
    """Draw a filled rectangle, clipping its edges to the canvas."""
    left = max(0, x)
    top = max(0, y)
    right = min(WIDTH, x + width)
    bottom = min(HEIGHT, y + height)
    if left >= right or top >= bottom:
        return

    pixel = bytes(color)
    row_pixels = pixel * (right - left)
    for row in range(top, bottom):
        offset = (row * WIDTH + left) * 3
        buffer[offset:offset + len(row_pixels)] = row_pixels


def hline(x, y, length, color):
    """Draw a horizontal line from x for length pixels, clipping as needed."""
    fill_rect(x, y, length, 1, color)


def vline(x, y, length, color):
    """Draw a vertical line from y for length pixels, clipping as needed."""
    fill_rect(x, y, 1, length, color)


def outline_rect(x, y, width, height, color):
    """Draw a one-pixel rectangular outline, clipped to the canvas."""
    if width <= 0 or height <= 0:
        return
    hline(x, y, width, color)
    if height > 1:
        hline(x, y + height - 1, width, color)
    if height > 2:
        vline(x, y + 1, height - 2, color)
        if width > 1:
            vline(x + width - 1, y + 1, height - 2, color)


# Each hand-drawn glyph is seven rows of five pixels. Lowercase letters use
# the same compact small-cap forms as uppercase, with explicit dictionary keys.
GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "#....", "####.", "....#", "....#", "####."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ".": (".....", ".....", ".....", ".....", ".....", "..##.", "..##."),
    ",": (".....", ".....", ".....", ".....", "..##.", "..##.", "...#."),
    "'": ("..##.", "..##.", "..#..", ".....", ".....", ".....", "....."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    ":": (".....", "..##.", "..##.", ".....", "..##.", "..##.", "....."),
    ";": (".....", "..##.", "..##.", ".....", "..##.", "..##.", "...#."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "&": (".##..", "#..#.", "#..#.", ".##..", "#.#.#", "#..#.", ".##.#"),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", ".#.##", "#..##"),
}
GLYPHS["·"] = (".....", ".....", ".....", "..#..", ".....", ".....", ".....")
GLYPHS["—"] = (".....", ".....", ".....", "#####", ".....", ".....", ".....")
GLYPHS.update({letter: GLYPHS[letter.upper()] for letter in "abcdefghijklmnopqrstuvwxyz"})


def draw_text(x, y, text, scale, color):
    """Draw text with a six-pixel cell advance, scaled uniformly."""
    if scale <= 0:
        raise ValueError("scale must be a positive integer")
    cursor_x = x
    for character in text:
        glyph = GLYPHS.get(character, GLYPHS["?"])
        for row_index, row in enumerate(glyph):
            for column_index, pixel in enumerate(row):
                if pixel == "#":
                    fill_rect(
                        cursor_x + column_index * scale,
                        y + row_index * scale,
                        scale,
                        scale,
                        color,
                    )
        cursor_x += 6 * scale
    return cursor_x


def text_width(text, scale=1):
    """Measure the visible width of a string, excluding its final cell gap."""
    if scale <= 0:
        raise ValueError("scale must be a positive integer")
    return max(0, len(text) * 6 * scale - scale)


def word_wrap(text, max_chars):
    """Wrap text at word boundaries, splitting words longer than max_chars."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    words = text.split()
    if not words:
        return []

    lines = []
    current = ""
    for word in words:
        while len(word) > max_chars:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:max_chars])
            word = word[max_chars:]
        if not word:
            continue
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_text_wrapped(x, y, text, scale, color, max_width_px, line_gap):
    """Wrap and draw text; return the bottom y-coordinate of the last line."""
    if scale <= 0:
        raise ValueError("scale must be a positive integer")
    if max_width_px <= 0:
        raise ValueError("max_width_px must be positive")
    max_chars = max(1, (max_width_px + scale) // (6 * scale))
    lines = word_wrap(text, max_chars)
    line_step = 7 * scale + line_gap
    for line_index, line in enumerate(lines):
        draw_text(x, y + line_index * line_step, line, scale, color)
    if not lines:
        return y
    return y + (len(lines) - 1) * line_step + 7 * scale


def _png_chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def encode_png():
    """Encode the current buffer as an 8-bit truecolor PNG."""
    raw = bytearray()
    stride = WIDTH * 3
    for y in range(HEIGHT):
        raw.append(0)
        start = y * stride
        raw.extend(buffer[start:start + stride])

    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _png_chunk(b"IEND", b"")
    )


def write_png(path):
    """Write a size-checked deterministic PNG at path."""
    png = encode_png()
    if len(png) > MAX_PNG_BYTES:
        raise ValueError("encoded PNG exceeds the 1 MiB size limit")
    with open(path, "wb") as output_file:
        output_file.write(png)


def draw_panel(x, y, width, title, body):
    fill_rect(x, y, width, 32, PANEL_TINT)
    draw_text(x + 8, y + 8, title, 2, ACCENT_RED)
    draw_text_wrapped(x + 8, y + 44, body, 1, INK, width - 16, 3)
    hline(x, y + 153, width, HAIRLINE)


def draw_regional_card(x, y, width, height, region, headline):
    outline_rect(x, y, width, height, HAIRLINE)
    draw_text(x + 8, y + 9, region, 2, ACCENT_RED)
    draw_text_wrapped(x + 8, y + 32, headline, 1, INK, width - 16, 3)


def main():
    global buffer
    buffer = bytearray(bytes(PAPER) * (WIDTH * HEIGHT))

    hline(32, 23, 936, INK)
    draw_text(32, 42, "THE WORLD TODAY", 7, INK)
    draw_text(32, 111, "Monday 23 November 2026 · All the day's news, in one image", 2, MUTED_GREY)
    hline(32, 145, 936, INK)
    hline(32, 149, 936, INK)

    draw_text(32, 168, "LEAD", 2, ACCENT_RED)
    draw_text(32, 192, "COP31 TALKS COLLAPSE IN ANTALYA", 4, INK)
    lead_body = (
        "The climate summit ends without a deal, as the EU and other blocs reject any text "
        "that omits a fossil-fuel phase-out. Australia's prime minister calls the failure a "
        "sign of 'difficult geopolitical times' — two weeks of talks, and the world leaves "
        "Antalya with nothing signed."
    )
    draw_text_wrapped(32, 241, lead_body, 2, INK, 936, 4)
    hline(32, 340, 936, INK)

    panel_y = 357
    panel_width = 304
    draw_panel(
        32,
        panel_y,
        panel_width,
        "HORMUZ ON A KNIFE-EDGE",
        "Iran strikes tankers and wounds two in Bahrain; Houthi fighters claim hits on Saudi oil sites. The UAE runs oil convoys through the strait under US escort.",
    )
    draw_panel(
        348,
        panel_y,
        panel_width,
        "DRONES REACH THE BALTIC",
        "Ukrainian drones hit Russia's Baltic fleet for the first time. A Russian cargo ship burns off Finland, and a strike near Kyiv leaves 14 people missing.",
    )
    draw_panel(
        664,
        panel_y,
        panel_width,
        "NO DEAL IN JERUSALEM",
        "Netanyahu's Likud and Eisenkot's Yashar end their unity talks without agreement, leaving Israel's government question open for another week.",
    )

    regions = [
        ("PYONGYANG", "Kim says North Korea seeks security, not supremacy, as its nuclear stockpile grows."),
        ("JAKARTA", "Factory fire - seven body bags recovered, 50 workers still missing."),
        ("JUBA", "24 civilians killed in fresh fighting in South Sudan."),
        ("GOMA", "WHO chief pleads for peace in Ebola-hit eastern DR Congo."),
        ("KHARTOUM", "Drone strikes hit homes and a UN building in Sudan's capital."),
        ("BRASILIA", "Bolsonaro is stable in intensive care, his aides say."),
        ("SINALOA", "Mexico captures the FBI's most-wanted cartel boss; 11 die in the firefights."),
        ("SEATTLE", "Father and daughter detained by ICE at the airport on their way to a family baptism."),
        ("LISBON", "Thousands march as the cost of living fuels anger."),
        ("GENEVA", "Nations agree to keep negotiating limits on lethal AI weapons."),
        ("SEOUL", "Education minister quits over an AI-driven exam cheating scandal."),
        ("SPORT", "Pochettino fumes at a red card in his nightmare Man United start; Sindarov takes White in Game 1 of the chess world final."),
    ]
    grid_x = (32, 348, 664)
    grid_y = (529, 623, 717, 811)
    for index, (region, headline) in enumerate(regions):
        column = index % 3
        row = index // 3
        draw_regional_card(grid_x[column], grid_y[row], panel_width, 88, region, headline)

    hline(32, 910, 936, INK)
    draw_text(32, 921, "DAY IN NUMBERS", 3, ACCENT_RED)
    numbers = (
        "0 deals reached at COP31 · 14 missing near Kyiv · 50 missing in the factory fire · "
        "24 killed in South Sudan · 11 dead in Sinaloa · 2 wounded in Bahrain."
    )
    draw_text_wrapped(32, 946, numbers, 1, INK, 936, 3)

    hline(32, 960, 936, HAIRLINE)
    draw_text(
        32,
        968,
        "Drawn by a Python program, standard library only · The World Today — Monday 23 November 2026",
        1,
        MUTED_GREY,
    )

    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)
    write_png(os.path.join(output_dir, "entry.png"))


if __name__ == "__main__":
    main()
