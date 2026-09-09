#!/usr/bin/env python3
"""Export native platform icons from gui/icon.svg (requires cairosvg and Pillow)."""
from pathlib import Path
import json,io
import cairosvg
from PIL import Image
r=Path(__file__).resolve().parents[1];app=r/'apps/lazytunnel'
svg=(r/'gui/icon.svg').read_bytes()
def png(path,size):
 path.parent.mkdir(parents=True,exist_ok=True)
 cairosvg.svg2png(bytestring=svg,write_to=str(path),output_width=size,output_height=size)
for platform in ['ios','macos']:
 root=app/platform/'Runner/Assets.xcassets/AppIcon.appiconset'
 d=json.loads((root/'Contents.json').read_text())
 for row in d['images']:
  if 'filename' in row:
   size=round(float(row['size'].split('x')[0])*float(row['scale'].rstrip('x')))
   png(root/row['filename'],size)
   if platform == 'ios':
    # App Store icons must be opaque, including the rounded-corner outside.
    icon=Image.open(root/row['filename']).convert('RGBA')
    background=Image.new('RGB',icon.size,'#087f70')
    background.paste(icon,mask=icon.getchannel('A'))
    background.save(root/row['filename'])
for dpi,size in [('mdpi',48),('hdpi',72),('xhdpi',96),('xxhdpi',144),('xxxhdpi',192)]:
 png(app/f'android/app/src/main/res/mipmap-{dpi}/ic_launcher.png',size)
buf=cairosvg.svg2png(bytestring=svg,output_width=256,output_height=256)
Image.open(io.BytesIO(buf)).save(app/'windows/runner/resources/app_icon.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('Native icons exported from the existing project SVG')
