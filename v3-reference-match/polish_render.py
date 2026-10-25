"""Polish the Blender render into a clean presentation image.

The Cycles pass deliberately renders the floor and its shadow, but Standard
view transform leaves the studio field slightly off-white.  This final step
only lifts the connected, neutral background to pure white and applies a mild
S-curve.  It does not paint, cut out or replace any part of the machine.
"""
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import binary_propagation, gaussian_filter

HERE = Path(__file__).resolve().parent
src = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'quality-upcycler-reference-match-raw.png'
out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / 'quality-upcycler-reference-match.png'
small = out.with_name(out.stem + '-small.png')

im = Image.open(src).convert('RGB')
a = np.asarray(im).astype(np.float32) / 255.0
mx = a.max(axis=2)
mn = a.min(axis=2)
lum = 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
sat = mx - mn

# Find the bright, nearly neutral floor region connected to the image edge.
# The cast shadow is darker and remains untouched; the machine silhouette
# is protected because it is not connected to the outer bright field.
bright = (lum > 0.70) & (sat < 0.075)
seed = np.zeros_like(bright)
seed[0, :] = bright[0, :]
seed[-1, :] = bright[-1, :]
seed[:, 0] = bright[:, 0]
seed[:, -1] = bright[:, -1]
bg = binary_propagation(seed, mask=bright)
bg = gaussian_filter(bg.astype(np.float32), sigma=1.0)
bg = np.clip((bg - 0.12) / 0.88, 0.0, 1.0)[..., None]

# White presentation field.
a = a * (1.0 - bg) + bg

# The reference asset has deeper, richer object mids than the raw Cycles
# pass.  Apply a restrained gamma/saturation lift only outside the white
# field, then a gentle S-curve.
obj = 1.0 - bg
a_obj = np.power(np.clip(a, 0, 1), 1.12)
lum2 = (0.2126 * a_obj[:, :, 0] + 0.7152 * a_obj[:, :, 1] +
        0.0722 * a_obj[:, :, 2])[..., None]
a_obj = np.clip(lum2 + (a_obj - lum2) * 1.06, 0, 1)
a = a * (1.0 - obj) + a_obj * obj
a = np.clip((a - 0.5) * 1.09 + 0.5, 0, 1)
a = np.where(bg > 0.995, 1.0, a)

result = Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8))
result.save(out)
result.resize((1000, 350), Image.Resampling.LANCZOS).save(small)
print('wrote', out)
print('wrote', small)


