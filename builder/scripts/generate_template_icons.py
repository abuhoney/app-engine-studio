#!/usr/bin/env python3
"""Generate minimal launcher icon PNGs for the Bardom-builder template."""
from PIL import Image
from pathlib import Path

import os
RES = Path("/home/z/my-project/bardom-builder/templates/app/src/main/res")

SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

def make_icon(size, round_shape=False):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Indigo background
    bg = Image.new("RGBA", (size, size), (99, 102, 241, 255))
    if round_shape:
        # Make it circular
        from PIL import ImageDraw
        mask = Image.new("L", (size, size), 0)
        d = ImageDraw.Draw(mask)
        d.ellipse([0, 0, size-1, size-1], fill=255)
        img.paste(bg, (0, 0), mask)
    else:
        # Rounded square
        from PIL import ImageDraw
        mask = Image.new("L", (size, size), 0)
        d = ImageDraw.Draw(mask)
        radius = size // 6
        d.rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=255)
        img.paste(bg, (0, 0), mask)
    # Add "B" letter in white (simple text via small image)
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    font_size = size // 2
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    text = "B"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1]
    d.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)
    return img

def _home_or_root():
    import os
    return os.environ.get("HOME", "")

for density, size in SIZES.items():
    out_dir = RES / density
    out_dir.mkdir(parents=True, exist_ok=True)
    make_icon(size, round_shape=False).save(out_dir / "ic_launcher.png")
    make_icon(size, round_shape=True).save(out_dir / "ic_launcher_round.png")
    print(f"Wrote {density}/ic_launcher.png + ic_launcher_round.png ({size}x{size})")

print("Done.")
