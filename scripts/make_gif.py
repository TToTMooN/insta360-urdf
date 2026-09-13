"""Pack rendered turntable PNGs into a looping, globally palettized GIF."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]/"models/x5"
files=sorted((ROOT/"preview/turntable_frames").glob("frame_*.png"))
if len(files)<4:raise SystemExit("Render at least four frames first")
font_path=Path("/System/Library/Fonts/Helvetica.ttc")
def font(size):
    return ImageFont.truetype(str(font_path),size) if font_path.exists() else ImageFont.load_default(size=size)
frames=[]
for file in files:
    source=Image.open(file).convert("RGBA")
    image=Image.new("RGB",(640,880),(236,238,241))
    image.paste(source,(0,45),source)
    draw=ImageDraw.Draw(image)
    draw.text((28,22),"INSTA360 X5",font=font(25),fill=(28,36,47))
    draw.text((28,839),"Independent visual reconstruction  |  GLB + URDF",font=font(17),fill=(79,89,102))
    frames.append(image)
# A shared palette avoids color flicker between animation frames.
samples=Image.new("RGB",(160*10,220*6))
for i,frame in enumerate(frames[:60]):
    samples.paste(frame.resize((160,220)),((i%10)*160,(i//10)*220))
palette=samples.quantize(colors=254,method=Image.Quantize.MEDIANCUT)
# Preserve the tiny status accents even though they occupy few pixels.
colors=palette.getpalette()[:254*3]+[42,124,145,48,137,154]
palette.putpalette(colors)
indexed=[frame.quantize(palette=palette,dither=Image.Dither.FLOYDSTEINBERG) for frame in frames]
indexed[0].save(ROOT/"preview/turntable.gif",save_all=True,append_images=indexed[1:],duration=80,loop=0,optimize=True,disposal=2)
print(f"Saved {len(frames)} frames: preview/turntable.gif")
