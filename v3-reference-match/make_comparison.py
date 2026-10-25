from pathlib import Path
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
ref = Image.open(HERE.parent / 'v3' / 'image.png').convert('RGB')
ren = Image.open(HERE / 'quality-upcycler-reference-match-small.png').convert('RGB')
canvas = Image.new('RGB', (1000, 730), 'white')
canvas.paste(ref, (0, 28))
canvas.paste(ren, (0, 404))
d = ImageDraw.Draw(canvas)
d.text((10, 8), 'REFERENCE: art/v3/image.png (1000 x 350)', fill=(60, 60, 60))
d.text((10, 383), 'BLENDER RENDER: procedural reference-match study (1000 x 350)', fill=(60, 60, 60))
d.line((0, 378, 1000, 378), fill=(210, 210, 210), width=1)
canvas.save(HERE / 'comparison-reference-vs-render.png')
print('wrote comparison-reference-vs-render.png')
