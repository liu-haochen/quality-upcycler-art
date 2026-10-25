"""Render idle/work base frames plus a working-only additive glow layer.

Idle state:
  - chamber task lights are off,
  - all machine windows/screens are dark,
  - small status lamps are red and non-emissive.

Working state:
  - chamber task lights pulse,
  - amber windows and green diagnostic screen are on,
  - status lamps are green and emissive,
  - a separate additive glow atlas is rendered for Factorio's
    working_visualisations so it survives nighttime darkening.
"""
import bpy
import os
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
BLEND = HERE / 'quality-upcycler-reference-match-animated.blend'
IDLE_DIR = HERE / 'animation-frames' / 'idle'
ONLY_GLOW = os.environ.get('QC_ONLY_GLOW') == '1'
WORK_DIR = HERE / 'animation-frames' / 'work'
GLOW_DIR = HERE / 'animation-frames' / 'work-glow'
STATIC_IDLE = HERE / 'animation-frames' / 'idle-static.png'
for d in (IDLE_DIR, WORK_DIR, GLOW_DIR):
    d.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
def use_gpu(scene):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.refresh_devices()
    for dev in prefs.devices:
        dev.use = (dev.type == 'OPTIX')
    scene.cycles.device = 'GPU'

use_gpu(scene)
floor = bpy.data.objects.get('White presentation floor')
if floor:
    floor.hide_render = True
scene.use_nodes = False
scene.render.film_transparent = True
scene.render.resolution_x = 320
scene.render.resolution_y = 320
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = -0.02

cam = bpy.data.objects['Reference-match orthographic camera']
cam.data.ortho_scale = 4.95
cam.location = Vector((3.05, -7.35, 9.35))
cam.rotation_euler = (Vector((0, 0, .92)) - cam.location).to_track_quat('-Z', 'Y').to_euler()


def make_principled(name, base, metallic, roughness, emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*base, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if emission is not None:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1)
        bsdf.inputs['Emission Strength'].default_value = strength
    m.diffuse_color = (*base, 1)
    return m


def make_emission(name, color, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = (*color, 1)
    em.inputs[1].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs[0])
    return m

# state materials
indicator_red = make_principled('STATE | idle red indicator', (.34, .008, .004),
                                .12, .42, emission=(.25, 0, 0), strength=0.0)
indicator_green = make_principled('STATE | working green indicator', (.018, .38, .022),
                                  .05, .30, emission=(.04, 1.0, .10), strength=3.2)
indicator_amber = make_principled('STATE | working amber indicator', (.30, .11, .012),
                                  .10, .34, emission=(1.0, .32, .035), strength=2.4)
indicator_red_work = make_principled('STATE | working red indicator', (.30, .006, .003),
                                     .10, .38, emission=(.95, .022, .006), strength=1.6)
screen_off = make_principled('STATE | idle dark screen', (.004, .018, .008),
                             .25, .38, emission=(0, 0, 0), strength=0.0)
screen_teal = make_principled('STATE | working teal screen', (.004, .045, .032),
                              .18, .40, emission=(.018, .34, .20), strength=1.25)
amber_off = make_principled('STATE | idle amber window off', (.028, .010, .002),
                            .25, .48, emission=(0, 0, 0), strength=0.0)

quality_defs = [
    ('uncommon', (.012, .16, .030), (.04, .62, .14)),
    ('rare', (.004, .055, .20), (.035, .18, .62)),
    ('epic', (.09, .018, .18), (.32, .07, .52)),
    ('legendary', (.18, .060, .006), (.68, .27, .030)),
]
quality_idle = [make_principled(f'STATE | quality {q} idle', base, .18, .34,
                                 emission=emis, strength=0.0)
                for q, base, emis in quality_defs]
quality_work = [make_principled(f'STATE | quality {q} work', base, .18, .30,
                                 emission=emis, strength=1.5)
                for q, base, emis in quality_defs]
overlay_quality = [make_emission(f'OVERLAY | quality {q}', emis, 0.75)
                   for q, base, emis in quality_defs]

glow_green = bpy.data.materials.get('Glow | green diagnostics')
glow_orange = bpy.data.materials.get('Glow | amber machining slot')
glow_red = bpy.data.materials.get('Glow | red indicators')

overlay_green = make_emission('OVERLAY | green glow', (.04, 1.0, .10), 1.15)
overlay_amber = make_emission('OVERLAY | amber glow', (1.0, .30, .018), 1.05)
overlay_teal = make_emission('OVERLAY | teal screen glow', (.016, .30, .19), 0.68)
overlay_red = make_emission('OVERLAY | red warning glow', (1.0, .035, .008), 0.9)
overlay_flow_head = make_emission('OVERLAY | flow head', (1.0, .86, .58), 1.65)
overlay_flow_mid = make_emission('OVERLAY | flow mid', (1.0, .42, .055), 1.35)
overlay_flow_tail = make_emission('OVERLAY | flow tail', (.72, .16, .015), 1.0)

# The single travelling comet changes hue from normal silver through the four
# upgrade qualities.  It returns to silver in the last few frames so the 32
# frame loop is seamless; the fade is masked by the comet's highest speed.
flow_palette = [
    (101, (0.72, 0.78, 0.86)),   # normal
    (108, (0.06, 1.00, 0.16)),   # uncommon
    (115, (0.05, 0.36, 1.00)),   # rare
    (122, (0.62, 0.12, 1.00)),   # epic
    (127, (1.00, 0.46, 0.045)),  # legendary
    (129, (1.00, 0.46, 0.045)),  # hold legendary briefly
    (132, (0.72, 0.78, 0.86)),   # wrap back to normal
]


def animate_flow_material(mat, gain):
    node = next(n for n in mat.node_tree.nodes if n.type == 'EMISSION')
    for frame, color in flow_palette:
        node.inputs[0].default_value = (min(1.0, color[0] * gain),
                                        min(1.0, color[1] * gain),
                                        min(1.0, color[2] * gain), 1.0)
        node.inputs[0].keyframe_insert('default_value', frame=frame)
    if mat.node_tree.animation_data and mat.node_tree.animation_data.action:
        for fc in mat.node_tree.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


animate_flow_material(overlay_flow_head, 1.00)
animate_flow_material(overlay_flow_mid, 0.72)
animate_flow_material(overlay_flow_tail, 0.42)

# Record original assignments and classify only the emissive pieces.
orig_assignments = {}
glow_objects = []
for o in scene.objects:
    if o.type not in {'MESH', 'CURVE'} or not hasattr(o.data, 'materials'):
        continue
    orig_assignments[o] = list(o.data.materials)
    mats = [m.name for m in o.data.materials if m is not None]
    if any(m.startswith('Glow |') for m in mats):
        glow_objects.append(o)


def classify(o):
    n = o.name.lower()
    mats = [m.name for m in orig_assignments[o] if m is not None]
    if 'flow ring' in n:
        return 'flow'
    if 'oversized module' in n and ('quality window' in n or 'quality window face' in n):
        return 'quality'
    if 'green screen' in n or 'green diagnostic screen' in n:
        return 'screen'
    if 'amber' in n or any(m == 'Glow | amber machining slot' for m in mats):
        return 'amber'
    if 'indicator' in n or 'beacon' in n:
        return 'status'
    if any(m == 'Glow | red indicators' for m in mats):
        return 'status'
    if any(m == 'Glow | green diagnostics' for m in mats):
        return 'screen'
    return 'status'


def quality_index(o):
    try:
        return int(o.name.rsplit(' ', 1)[-1]) % 4
    except Exception:
        return 0


def indicator_kind(o):
    n = o.name.lower()
    if 'arm red indicator' in n:
        return 'red'
    if 'status beacon' in n:
        try:
            idx = int(n.split('beacon ')[1].split()[0])
        except Exception:
            idx = 0
        # Two-cell beacons: the cell pair carries a green/amber or amber/red
        # combination instead of collapsing into one colour at game scale.
        if 'cell 1' in n:
            return 'amber' if idx in (0, 2, 4) else 'red'
        return 'green' if idx in (0, 2, 4) else 'amber'
    if 'front service indicator' in n:
        try:
            idx = int(n.rsplit(' ', 1)[-1])
        except Exception:
            idx = 0
        return 'green' if idx in (0, 6) else 'amber'
    if 'upper rim indicator' in n:
        try:
            idx = int(n.rsplit(' ', 1)[-1])
        except Exception:
            idx = 0
        return 'green' if idx in (4, 8) else 'amber'
    if 'inner wall red beacon' in n:
        return 'amber'
    return 'green'


def set_state(state):
    for o in glow_objects:
        n = o.name.lower()
        cat = classify(o)
        kind = indicator_kind(o) if cat == 'status' else None
        qidx = quality_index(o) if cat == 'quality' else None
        if state == 'idle':
            if cat == 'flow':
                o.hide_render = True
                continue
            if cat == 'quality':
                mat = quality_idle[qidx]
            else:
                mat = indicator_red if cat == 'status' else screen_off if cat == 'screen' else amber_off
        elif state == 'work':
            if cat == 'flow':
                o.hide_render = True
                continue
            if cat == 'quality':
                mat = quality_work[qidx]
            elif cat == 'status':
                mat = indicator_green if kind == 'green' else indicator_red_work if kind == 'red' else indicator_amber
            elif cat == 'screen':
                mat = screen_teal
            else:
                mat = glow_orange
        else:
            if cat == 'flow':
                o.hide_render = False
                if 'head' in n:
                    mat = overlay_flow_head
                elif 'part' in n and int(n.rsplit(' ', 1)[-1]) <= 8:
                    mat = overlay_flow_mid
                else:
                    mat = overlay_flow_tail
            elif cat == 'quality':
                mat = overlay_quality[qidx]
            elif cat == 'status':
                mat = overlay_green if kind == 'green' else overlay_red if kind == 'red' else overlay_amber
            elif cat == 'screen':
                mat = overlay_teal
            else:
                mat = overlay_amber
        o.data.materials.clear()
        o.data.materials.append(mat)

# --- batch helpers ----------------------------------------------------------
# Render each state as one animation sequence.  With Cycles on the GPU this is
# important: rendering frames one-by-one triggered a kernel reload per still
# image, while an animation sequence compiles once and reuses the scene.
scene.render.use_persistent_data = True


def render_sequence(frame_start, frame_end, prefix, out_dir):
    for old in out_dir.glob(prefix + '*.png'):
        old.unlink()
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    scene.render.filepath = str(out_dir / prefix)
    bpy.ops.render.render(animation=True)
    for i, scene_frame in enumerate(range(frame_start, frame_end + 1), start=1):
        src = out_dir / f'{prefix}{scene_frame:04d}.png'
        dst = out_dir / f'{prefix}{i:04d}.png'
        if src.exists():
            src.replace(dst)


# --- idle: machine not glowing, red non-emissive indicators -----------------
if not ONLY_GLOW:
    set_state('idle')
    render_sequence(1, 32, 'idle-', IDLE_DIR)

    # --- working: warm/mixed segmented indicators ---------------------------
    set_state('work')
    render_sequence(101, 132, 'work-', WORK_DIR)

    # A single idle hold pose taken from the working cycle's final safe pose.
    # The state machine uses this as the rest sprite, so work -> idle changes
    # only the illuminated materials, not the arm/carriage positions.
    set_state('idle')
    scene.frame_set(132)
    scene.render.filepath = str(STATIC_IDLE)
    bpy.ops.render.render(write_still=True)

# --- working-only glow overlay ---------------------------------------------
# The glow must still respect the machine's real depth order.  Previously all
# non-emissive geometry was hidden, so lamps and screens behind arms, rings and
# separator bars leaked through the additive layer.  Use Holdout materials on
# every non-glow mesh instead: they punch transparent holes wherever a solid
# part would occlude the light, while leaving visible emissive surfaces intact.
glow_set = set(glow_objects)
holdout = bpy.data.materials.new('OVERLAY | geometry holdout')
holdout.use_nodes = True
nt = holdout.node_tree
nt.nodes.clear()
h = nt.nodes.new('ShaderNodeHoldout')
out = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(h.outputs[0], out.inputs[0])
for o in scene.objects:
    if o.type in {'MESH', 'CURVE'}:
        if o not in glow_set:
            o.data.materials.clear()
            o.data.materials.append(holdout)
    elif o.type == 'LIGHT':
        o.hide_render = True
if floor:
    floor.hide_render = True
for n in scene.world.node_tree.nodes:
    if n.type == 'BACKGROUND':
        n.inputs['Strength'].default_value = 0.0
set_state('overlay')
render_sequence(101, 132, 'glow-', GLOW_DIR)

print('Rendered idle, working and glow-overlay frames.')
