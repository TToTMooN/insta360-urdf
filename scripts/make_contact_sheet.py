"""Arrange our own rendered views on a publication-friendly neutral background."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]/"models/x5"
canvas=Image.new("RGB",(1800,1340),(236,238,241))
draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",32) if Path("/System/Library/Fonts/Helvetica.ttc").exists() else ImageFont.load_default(size=32)
small=ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",21) if Path("/System/Library/Fonts/Helvetica.ttc").exists() else ImageFont.load_default(size=21)
draw.text((65,42),"INSTA360 X5  /  PROCEDURAL VISUAL ASSET",fill=(27,35,44),font=font)
draw.text((65,88),"46 × 124.5 × 38.2 mm    ·    0.20 kg    ·    Independent reconstruction",fill=(84,94,106),font=small)
for i,name in enumerate(["front","rear"]):
    im=Image.open(ROOT/"preview"/(name+".png")).convert("RGBA")
    im.thumbnail((850,1120),Image.Resampling.LANCZOS)
    canvas.paste(im,(35+i*900+(850-im.width)//2,155),im)
    draw.text((80+i*900,1270),"FRONT / CONTROL SIDE" if i==0 else "REAR / BATTERY SIDE",fill=(64,74,85),font=small)
canvas.save(ROOT/"preview/contact_sheet.png")

# True orthographic views make screen dimensions and side placement inspectable.
sheet=Image.new('RGB',(2200,1100),(236,238,241))
draw=ImageDraw.Draw(sheet)
draw.text((40,25),'INSTA360 X5',font=font,fill=(27,35,44))
for i,(name,label) in enumerate([('front_ortho','SCREEN FRONT'),('controls_ortho','CONTROLS  /  +Y'),('rear_ortho','REAR'),('battery_ortho','BATTERY  /  -Y')]):
    im=Image.open(ROOT/'preview'/(name+'.png')).convert('RGBA')
    im=im.crop(im.getbbox())
    im.thumbnail((430,880),Image.Resampling.LANCZOS)
    sheet.paste(im,(i*550+(550-im.width)//2,90),im)
    draw.text((i*550+90,1050),label,font=small,fill=(64,74,85))
sheet.save(ROOT/'preview/orthographic_sheet.png')


# All panels share one crop and scale; the last shows the opposite side.
collision_paths=[ROOT/'preview'/name for name in ['front.png','collision_overlay.png','collision_only.png','collision_rear.png']]
if all(p.exists() for p in collision_paths):
    images=[Image.open(p).convert('RGBA') for p in collision_paths]
    boxes=[im.getbbox() for im in images]
    bounds=(min(b[0] for b in boxes)-15,min(b[1] for b in boxes)-15,
            max(b[2] for b in boxes)+15,max(b[3] for b in boxes)+15)
    collision_sheet=Image.new('RGB',(2400,1100),(236,238,241))
    draw=ImageDraw.Draw(collision_sheet)
    draw.text((45,28),'INSTA360 X5  /  COLLISION',font=font,fill=(27,35,44))
    for i,(im,label) in enumerate(zip(images,['VISUAL','COLLISION OVERLAY','COLLISION / FRONT','COLLISION / REAR'])):
        im=im.crop(bounds)
        im.thumbnail((510,860),Image.Resampling.LANCZOS)
        collision_sheet.paste(im,(i*600+(600-im.width)//2,115),im)
        draw.text((i*600+75,1005),label,font=small,fill=(64,74,85))
    for x,label,color in [(930,'Body',(44,154,174)),(1115,'Front lens',(220,136,59)),(1345,'Rear lens',(148,106,188))]:
        draw.ellipse((x,1060,x+15,1075),fill=color)
        draw.text((x+25,1054),label,font=small,fill=(64,74,85))
    collision_sheet.save(ROOT/'preview/collision_sheet.png')
