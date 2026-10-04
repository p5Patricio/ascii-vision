"""Generate the application icon (PNG for the window, multi-size ICO for the Windows .exe/installer).

    python packaging/make_icon.py

The mark is three ASCII "shades" glyphs on a dark tile, matching the product's look.
"""
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "src", "ascii_vision", "assets", "fonts", "JetBrainsMono-Regular.ttf")
SIZE = 1024
CYAN = (25, 224, 255)


def render() -> Image.Image:
    tile = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((40, 40, SIZE - 40, SIZE - 40), radius=220, fill=255)

    # vertical gradient background
    grad = Image.new("RGBA", (SIZE, SIZE))
    px = ImageDraw.Draw(grad)
    for y in range(SIZE):
        k = y / SIZE
        px.line((0, y, SIZE, y), fill=(int(14 + 6 * k), int(26 + 10 * k), int(54 + 22 * k), 255))
    tile.paste(grad, (0, 0), mask)

    # border
    border = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle((40, 40, SIZE - 40, SIZE - 40), radius=220, outline=CYAN + (170,), width=14)
    tile = Image.alpha_composite(tile, border)

    # glyphs with glow
    font = ImageFont.truetype(FONT, 330)
    text = "▒@░"
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = d.textlength(text, font=font)
    d.text(((SIZE - w) / 2, SIZE / 2 - 205), text, font=font, fill=CYAN + (255,))
    glow = layer.filter(ImageFilter.GaussianBlur(28))
    glow.putalpha(ImageChops.multiply(glow.getchannel("A"), Image.new("L", (SIZE, SIZE), 190)))
    tile = Image.alpha_composite(tile, glow)
    tile = Image.alpha_composite(tile, layer)
    return tile


if __name__ == "__main__":
    icon = render()
    png = os.path.join(HERE, "..", "src", "ascii_vision", "assets", "icon.png")
    icon.resize((256, 256), Image.LANCZOS).save(png)
    icon.save(os.path.join(HERE, "app.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote", os.path.normpath(png), "and packaging/app.ico")
