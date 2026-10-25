"""Pack idle/working/glow Blender frames into Factorio atlases and animation.lua.

The working animation gets a separate additive glow atlas as a layer of the
same animation stack.  This keeps green indicator lamps and amber chamber
lights readable at night and avoids item-to-item glow desynchronization, while
the idle atlas contains only red, unlit status lamps and no machine glow.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import json

HERE = Path(__file__).resolve().parent
OUT = HERE / 'installed-graphics'
OUT.mkdir(parents=True, exist_ok=True)
FR = HERE / 'animation-frames'

idle = [Image.open(FR / 'idle' / f'idle-{i:04d}.png').convert('RGBA') for i in range(1, 33)]
idle_static = Image.open(FR / 'idle-static.png').convert('RGBA')
work = [Image.open(FR / 'work' / f'work-{i:04d}.png').convert('RGBA') for i in range(1, 33)]
glow_raw = [Image.open(FR / 'work-glow' / f'glow-{i:04d}.png').convert('RGBA') for i in range(1, 33)]

# Add a soft bloom around the emissive shapes.  Factorio draws this layer with
# draw_as_glow + additive blending, so the halo remains visible at night.
glow = []
for im in glow_raw:
    # Keep the bloom tight: wide halos merged nearby status cells into one
    # colour blob at Factorio's 0.5 sprite scale.
    halo = im.filter(ImageFilter.GaussianBlur(1.6))
    halo.putalpha(halo.getchannel('A').point(lambda a: round(a * .46)))
    wide = im.filter(ImageFilter.GaussianBlur(3.0))
    wide.putalpha(wide.getchannel('A').point(lambda a: round(a * .09)))
    layer = Image.alpha_composite(wide, halo)
    layer = Image.alpha_composite(layer, im)
    glow.append(layer)

boxes = [im.getbbox() for im in idle + work]
u = (min(b[0] for b in boxes), min(b[1] for b in boxes),
     max(b[2] for b in boxes), max(b[3] for b in boxes))
assert u[0] >= 0 and u[1] >= 0 and u[2] <= 320 and u[3] <= 320, u
sx = (160 - (u[0] + u[2]) / 2) * .5
sy = (160 - (u[1] + u[3]) / 2) * .5

# 8 x 4 atlas, 32 frames each.
def atlas(frames):
    img = Image.new('RGBA', (2560, 1280))
    for i, im in enumerate(frames):
        img.paste(im, ((i % 8) * 320, (i // 8) * 320))
    return img

atlas(idle).save(OUT / 'quality-upcycler-idle-animation.png')
idle_static.save(OUT / 'quality-upcycler-idle-static.png')
atlas(work).save(OUT / 'quality-upcycler-animation.png')
atlas(glow).save(OUT / 'quality-upcycler-glow-animation.png')

# Static projected shadow: blur alpha a little and keep it light enough not to
# overpower the machine.  Same world scale and origin as the 320 px frames.
shadow = Image.open(HERE / 'quality-upcycler-shadow-raw.png').convert('RGBA')
assert shadow.size == (480, 480)
shadow.putalpha(shadow.getchannel('A').filter(ImageFilter.GaussianBlur(1.2))
                .point(lambda a: round(a * .70)))
shadow.save(OUT / 'quality-upcycler-shadow.png')

# Icon from the working frame with green indicators and active glow.
icon_source = Image.alpha_composite(work[12], glow[12])
icon = icon_source.crop(u)
icon.thumbnail((60, 60), Image.Resampling.LANCZOS)
canvas = Image.new('RGBA', (64, 64))
canvas.paste(icon, ((64 - icon.width) // 2, (64 - icon.height) // 2))
canvas.save(OUT / 'quality-upcycler-icon.png')

# Preview sheet with the same body/shadow shifts used by Factorio.
def preview(im, glow_layer=None, grid=False):
    c = Image.new('RGBA', (480, 480), (86, 77, 55, 255))
    d = ImageDraw.Draw(c)
    if grid:
        for a in range(16, 480, 64):
            d.line((a, 0, a, 480), fill=(115, 101, 70))
            d.line((0, a, 480, a), fill=(115, 101, 70))
    pos = (round(sx * 2), round(sy * 2))
    c.alpha_composite(shadow, pos)
    c.alpha_composite(im, (80 + pos[0], 80 + pos[1]))
    if glow_layer is not None:
        c.alpha_composite(glow_layer, (80 + pos[0], 80 + pos[1]))
    if grid:
        ImageDraw.Draw(c).rectangle((144, 144, 335, 335), outline=(230, 172, 68), width=2)
    return c.convert('RGB')

preview(idle[0], None, True).save(HERE / 'footprint-idle-preview.png')
preview(work[12], glow[12], True).save(HERE / 'footprint-work-preview.png')
preview(idle[0]).save(HERE / 'preview-idle.png')
preview(work[12], glow[12]).save(HERE / 'preview-work.png')

# Approximate Factorio's night presentation: darken the base body, then add
# the working-only glow atlas additively.  This is a preview, not a game
# screenshot, but it checks the red-idle / green-night-working hierarchy.
def night_preview(im, glow_layer=None):
    c = Image.new('RGBA', (480, 480), (18, 20, 16, 255))
    pos = (round(sx * 2), round(sy * 2))
    sh = shadow.copy()
    sh.putalpha(sh.getchannel('A').point(lambda a: round(a * .40)))
    c.alpha_composite(sh, pos)
    r, g, b, a = im.split()
    dark = Image.merge('RGBA', (
        r.point(lambda v: round(v * .43)),
        g.point(lambda v: round(v * .43)),
        b.point(lambda v: round(v * .50)), a))
    c.alpha_composite(dark, (80 + pos[0], 80 + pos[1]))
    if glow_layer is not None:
        glow_canvas = Image.new('RGBA', (480, 480), (0, 0, 0, 0))
        glow_canvas.alpha_composite(glow_layer, (80 + pos[0], 80 + pos[1]))
        glow_rgb = Image.composite(glow_canvas.convert('RGB'),
                                   Image.new('RGB', (480, 480), 'black'),
                                   glow_canvas.getchannel('A'))
        c_rgb = ImageChops.add(c.convert('RGB'), glow_rgb)
        c = Image.merge('RGBA', (*c_rgb.split(), Image.new('L', (480, 480), 255)))
    return c.convert('RGB')

night_idle = night_preview(idle[0])
night_work = night_preview(work[12], glow[12])
night_idle.save(HERE / 'night-idle-preview.png')
night_work.save(HERE / 'night-work-preview.png')
comp = Image.new('RGB', (960, 510), (18, 20, 16))
comp.paste(night_idle, (0, 30)); comp.paste(night_work, (480, 30))
d = ImageDraw.Draw(comp)
d.text((24, 10), 'NIGHT IDLE (no glow, red indicators)', fill='white')
d.text((504, 10), 'NIGHT WORKING (mixed segmented glow)', fill='white')
comp.save(HERE / 'night-idle-vs-working.png')

# Side-by-side idle / working pose.
a = preview(idle[0]); b = preview(work[12], glow[12])
comp = Image.new('RGB', (960, 510), (45, 43, 38))
comp.paste(a, (0, 30)); comp.paste(b, (480, 30))
d = ImageDraw.Draw(comp)
d.text((24, 10), 'IDLE (red indicators, no glow)', fill='white')
d.text((504, 10), 'WORKING (mixed segmented indicators)', fill='white')
comp.save(HERE / 'idle-vs-working.png')

# Animated GIF previews.
frames = [preview(im, gl).resize((480, 480), Image.Resampling.LANCZOS)
          for im, gl in zip(work, glow)]
frames[0].save(HERE / 'quality-upcycler-working.gif', save_all=True,
               append_images=frames[1:], duration=60, loop=0)
idle_frames = [preview(im).resize((480, 480), Image.Resampling.LANCZOS) for im in idle]
idle_frames[0].save(HERE / 'quality-upcycler-idle.gif', save_all=True,
                    append_images=idle_frames[1:], duration=130, loop=0)

metadata = {
    'frame_width': 320, 'frame_height': 320, 'scale': .5,
    'frames': 32, 'line_length': 8,
    'shift_pixels': [sx, sy],
    'visible_union': list(u),
    'visible_size_game_pixels': [(u[2] - u[0]) * .5, (u[3] - u[1]) * .5],
    'idle_animation_speed': .12,
    'working_animation_speed': .50,
    'idle_state': 'red indicators, all task lights and screens off',
    'working_state': 'mixed warm/cyan/green work lighting, additive glow layer in the same stack, pulsed amber chamber',
    'shadow_alpha': .70,
    'shadow_projection': {'x_z': 1.15, 'y_z': .40},
    'palette': 'premium blue-teal steel / silver-blue armour / brushed brass manipulators',
    'ambient_fill': 'world + right fill + overhead + lower-left front fill for readable side structure',
    'glow_layer': 'working_visualisation with draw_in_states=working and fadeout',
    'visual_states': 'idle is a static safe-pose hold; working state duration is 32 animation frames (one full cycle at animation_speed 0.50); glow/lights fade on inactive and the body completes the current state before returning to idle',
    'glow_occlusion': 'Cycles emission pass rendered with Holdout occluders on all non-glow geometry',
    'working_lights': 'warm amber primary working light + low-intensity green status accent, both fadeout=true',
    'indicator_layout': 'low-saturation teal-green industrial status matrix with extra metal grille ribs',
    'bloom': 'very tight two-radius bloom plus widely spaced modules to keep colours separate',
    'flow_ring': 'single comet, one accelerated full lap, normal->uncommon->rare->epic->legendary colour progression',
    'quality_modules': 'neutral metal housings with small low-saturation quality windows: uncommon green / rare blue / epic purple / legendary orange',
    'arm_choreography': 'each arm rides its own carriage on the circular rail with independent arcs and timings; elbow folds during travel and extends for press/shear at its station',
    'table_motion': 'small oscillating shear sweep',
    'gpu_renderer': 'Cycles OptiX on NVIDIA RTX 4060 Laptop GPU; state batches rendered as animation sequences',
    'clearance_fixes': 'front-left reduction gear moved 0.19 toward camera and scaled to 86% to clear service boxes and auxiliary motor',
}
(HERE / 'animation-metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')

(OUT / 'animation.lua').write_text('''-- Generated by art/v3-reference-match/pack_animation.py.
-- Visual-state machine: idle rest pose and working cycle share the same
-- mechanical safe pose.  The glow/light layers fade when production stops.
local path="__quality-upcycler__/graphics/"
local shift=util.by_pixel(%.8f,%.8f)
local shadow_idle={filename=path.."quality-upcycler-shadow.png",width=480,height=480,scale=0.5,shift=shift,draw_as_shadow=true}
local shadow_work={filename=path.."quality-upcycler-shadow.png",width=480,height=480,scale=0.5,shift=shift,draw_as_shadow=true,repeat_count=32}
local glow={filename=path.."quality-upcycler-glow-animation.png",width=320,height=320,line_length=8,frame_count=32,animation_speed=0.50,scale=0.5,shift=shift,draw_as_glow=true,blend_mode="additive",priority="high"}
local base_work={filename=path.."quality-upcycler-animation.png",width=320,height=320,line_length=8,frame_count=32,animation_speed=0.50,scale=0.5,shift=shift}
local idle_static={filename=path.."quality-upcycler-idle-static.png",width=320,height=320,scale=0.5,shift=shift}
return {
  -- VisualState.duration is in animation frames.  One working state is one
  -- full 32-frame cycle at animation_speed 0.50.  Body layers stay drawn for
  -- the state; glow and physical lights fade when production becomes inactive.
  states={
    {name="idle",duration=1,next_active="working",next_inactive="idle"},
    {name="working",duration=32,next_active="working",next_inactive="idle"}
  },
  idle_animation={layers={shadow_idle,idle_static}},
  working_visualisations={
    {always_draw=true,draw_in_states={"working"},animation={layers={base_work,shadow_work}}},
    {always_draw=true,draw_in_states={"working"},fadeout=true,animation={layers={glow}}},
    {fadeout=true,light={intensity=0.95,size=12,shift={0,0.08},color={r=1.0,g=0.50,b=0.15}}},
    {fadeout=true,light={intensity=0.12,size=4.5,shift={0,-0.10},color={r=0.18,g=1.0,b=0.25}}}
  },
  always_draw_idle_animation=false,
  reset_animation_when_frozen=true
}
''' % (sx, sy), encoding='utf8')
print('visible union', u, 'game size', metadata['visible_size_game_pixels'], 'shift', [sx, sy])
print('wrote', OUT)






