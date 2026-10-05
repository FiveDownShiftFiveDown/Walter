"""Draws Walter's app icon and writes every size Tauri needs into src-tauri/icons."""
import pathlib
from PIL import Image, ImageDraw
OUT = pathlib.Path(__file__).resolve().parent.parent / "src-tauri" / "icons"
OUT.mkdir(parents=True, exist_ok=True)
S = 1024 * 4  # draw big, scale down for smooth edges
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
u = S / 1024
d.rounded_rectangle([40*u, 40*u, 984*u, 984*u], radius=200*u, fill=(27, 34, 32, 255))        # ink tile
d.rounded_rectangle([40*u, 40*u, 984*u, 984*u], radius=200*u, outline=(31, 95, 139, 255), width=int(28*u))
pts = [(232, 300), (372, 700), (512, 420), (652, 700), (792, 300)]                              # the W
d.line([(x*u, y*u) for x, y in pts], fill=(242, 244, 241, 255), width=int(104*u), joint="curve")
for x, y in (pts[0], pts[-1]):
    d.ellipse([(x-52)*u, (y-52)*u, (x+52)*u, (y+52)*u], fill=(242, 244, 241, 255))
d.rounded_rectangle([232*u, 790*u, 792*u, 850*u], radius=30*u, fill=(43, 122, 75, 255))          # green "progress" bar
big = img.resize((1024, 1024), Image.LANCZOS)
big.save(OUT / "app-icon.png")
for name, px in (("32x32.png", 32), ("128x128.png", 128), ("128x128@2x.png", 256), ("icon.png", 512)):
    big.resize((px, px), Image.LANCZOS).save(OUT / name)
big.save(OUT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icons written to", OUT)
