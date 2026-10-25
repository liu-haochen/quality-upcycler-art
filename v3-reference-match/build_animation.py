"""Rig the reference-match machine and author idle + working animation.

The model is intentionally kept in its static .blend and animated on top:
- arms are shrunk slightly around their mounting bearing (the user found the
  static arms oversized),
- shoulder / elbow / wrist empties are created for all three manipulators,
- external and internal gears receive their own rotation rigs,
- one action stores 32-frame idle and 32-frame working cycles,
- chamber task lights pulse during the working cycle.
"""
import bpy
import math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

HERE = Path(__file__).resolve().parent
SRC = HERE / 'quality-upcycler-reference-match.blend'
DST = HERE / 'quality-upcycler-reference-match-animated.blend'

bpy.ops.wm.open_mainfile(filepath=str(SRC))
scene = bpy.context.scene
scene.render.fps = 60

ARM_TAGS = [
    ('Left primary manipulator', 148.0),
    ('Right primary manipulator', 54.0),
    ('Front auxiliary manipulator', -31.0),
]
ARM_SHRINK = 0.86


def world_pos(o):
    return o.matrix_world.translation.copy()


def attach_preserve_world(o, parent):
    world = o.matrix_world.copy()
    o.parent = parent
    o.matrix_parent_inverse = parent.matrix_world.inverted()
    o.matrix_world = world


def make_empty(name, pos, parent=None, display=.07):
    e = bpy.data.objects.new(name, None)
    scene.collection.objects.link(e)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = display
    e.matrix_world = Matrix.Translation(Vector(pos))
    if parent is not None:
        attach_preserve_world(e, parent)
    e.rotation_mode = 'QUATERNION'
    return e


rigs = {}
for tag, base_a in ARM_TAGS:
    arm_objects = [o for o in scene.objects if o.name.startswith(tag)]
    base_obj = scene.objects[tag + ' base bearing']
    base = world_pos(base_obj)
    # Uniform shrink around the mounting bearing: smaller mass and a slightly
    # shorter reach, while the base itself stays bolted to the ring.
    world_scale = (Matrix.Translation(base) @
                   Matrix.Diagonal((ARM_SHRINK, ARM_SHRINK, ARM_SHRINK, 1.0)) @
                   Matrix.Translation(-base))
    for o in arm_objects:
        suffix = o.name[len(tag):].strip()
        if suffix.startswith('base bearing') or suffix.startswith('base ring'):
            continue
        o.matrix_world = world_scale @ o.matrix_world

    shoulder_pos = world_pos(scene.objects[tag + ' shoulder dark hub'])
    elbow_pos = world_pos(scene.objects[tag + ' elbow dark hub'])
    wrist_pos = world_pos(scene.objects[tag + ' wrist dark hub'])
    orbit = make_empty('RIG | ' + tag + ' | orbit', (0, 0, 0), display=.18)
    orbit.rotation_mode = 'XYZ'
    root = make_empty('RIG | ' + tag + ' | base', base, parent=orbit, display=.10)
    root.rotation_mode = 'XYZ'
    for o in arm_objects:
        suffix = o.name[len(tag):].strip().lower()
        if suffix.startswith('base bearing') or suffix.startswith('base ring'):
            attach_preserve_world(o, orbit)
    shoulder = make_empty('RIG | ' + tag + ' | shoulder', shoulder_pos, root)
    elbow = make_empty('RIG | ' + tag + ' | elbow', elbow_pos, shoulder)
    wrist = make_empty('RIG | ' + tag + ' | wrist', wrist_pos, elbow)

    for o in arm_objects:
        suffix = o.name[len(tag):].strip().lower()
        if suffix.startswith('base bearing') or suffix.startswith('base ring'):
            continue
        if any(k in suffix for k in ('tool', 'gripper', 'wrench')):
            attach_preserve_world(o, wrist)
        elif any(k in suffix for k in ('forearm', 'wrist')):
            attach_preserve_world(o, elbow)
        else:
            attach_preserve_world(o, shoulder)

    axis = Vector((-math.sin(math.radians(base_a)),
                   math.cos(math.radians(base_a)), 0.0)).normalized()
    rigs[tag] = {'orbit': orbit, 'root': root, 'shoulder': shoulder, 'elbow': elbow, 'wrist': wrist,
                 'axis': axis, 'phase': base_a}

# ---------------------------------------------------------------------------
# gear rigs
# ---------------------------------------------------------------------------
GEAR_SPECS = [
    ('Front-left exposed reduction gear', (0, 1, 0), 1.0),
    ('Right rear small exposed gear', (0, 1, 0), -1.35),
    ('Lower rear idler gear', (0, 1, 0), 1.55),
    ('Rear internal reduction gear', (0, 1, 0), -0.75),
    ('Rear internal pinion', (0, 1, 0), 1.9),
]
gear_rigs = []
for prefix, axis, speed in GEAR_SPECS:
    parts = [o for o in scene.objects if o.name.startswith(prefix)]
    if not parts:
        continue
    web = scene.objects.get(prefix + ' web')
    if web is None:
        continue
    if prefix == 'Front-left exposed reduction gear':
        # This gear was cutting through the left service junction box and the
        # adjacent auxiliary motor.  Pull the whole rotating assembly toward
        # the camera and shrink it slightly, keeping it visually attached to
        # its mount but giving its teeth real clearance.
        shift = Matrix.Translation(Vector((-.015, -.19, .025)))
        for o in parts:
            o.matrix_world = shift @ o.matrix_world
        center = world_pos(web)
        shrink = (Matrix.Translation(center) @
                  Matrix.Diagonal((.86, .86, .86, 1.0)) @
                  Matrix.Translation(-center))
        for o in parts:
            o.matrix_world = shrink @ o.matrix_world
    center = world_pos(web)
    rig = make_empty('RIG | gear | ' + prefix, center, display=.05)
    rig.rotation_mode = 'XYZ'
    for o in parts:
        attach_preserve_world(o, rig)
    gear_rigs.append((rig, axis, speed))

# ---------------------------------------------------------------------------
# Add a handful of larger state lamps.  The model's original green/red dots
# are only a few pixels in the game sprite; these make the idle-red /
# working-green distinction legible.  They are fixed service beacons attached
# to the outer shell and are re-coloured by render_animation.py.
# ---------------------------------------------------------------------------
def add_status_beacon(index, angle_deg, z, radius):
    a = math.radians(angle_deg)
    n = Vector((math.cos(a), math.sin(a), 0.0))
    t = Vector((-math.sin(a), math.cos(a), 0.0))
    p = Vector((math.cos(a) * 1.64, math.sin(a) * 1.64, z))
    # Dark, generously sized housing so the two cells stay separate at 0.5 scale.
    bpy.ops.mesh.primitive_cube_add(size=1, location=p)
    housing = bpy.context.object
    housing.name = f'STATE status beacon {index} housing'
    housing.dimensions = (.262, .062, .112)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    housing.rotation_euler.z = a + math.pi / 2
    housing.data.materials.append(bpy.data.materials['Iron | black oiled recess'])
    bev = housing.modifiers.new('soft beacon edge', 'BEVEL'); bev.width = .008; bev.segments = 2
    # Brass inner bezel remains visible as the gap between the two cells.
    bpy.ops.mesh.primitive_cube_add(size=1, location=p + n * .036)
    bezel = bpy.context.object
    bezel.name = f'STATE status beacon {index} brass bezel'
    bezel.dimensions = (.245, .016, .095)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bezel.rotation_euler.z = a + math.pi / 2
    bezel.data.materials.append(bpy.data.materials['Brass | small worn fittings'])
    glow_red = bpy.data.materials['Glow | red indicators']
    for j, off in enumerate((-.055, .055)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=p + n * .047 + t * off)
        cell = bpy.context.object
        cell.name = f'STATE status beacon {index} indicator cell {j}'
        cell.dimensions = (.078, .012, .060)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        cell.rotation_euler.z = a + math.pi / 2
        cell.data.materials.append(glow_red)

for i, (a, z, rr) in enumerate([(-160, .59, .056), (-112, .60, .060),
                                (-64, .61, .056), (18, .60, .052)]):
    add_status_beacon(i, a, z, rr)

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# rotating work-table rig.  A back-and-forth index sweep is used instead of a
# one-way 45-degree step so the animation loops without a visible snap.
# ---------------------------------------------------------------------------
TABLE_PREFIXES = (
    'Rotary index platter', 'Rotary platter', 'Platter index tooth',
    'Platter tooth bolt', 'Central machining bed', 'Central bed bright top',
    'Bed edge rail', 'Bed end rail', 'Central fixed jaw',
    'Central sliding jaw', 'Jaw clamp wedge', 'Clamped steel workpiece',
    'Workpiece upper plate', 'Clamp pressure cylinder', 'Clamp dark cap',
    'Clamp brass nut', 'Front vise body', 'Vise adjustment wheel',
    'Vise wheel hub', 'Precision table dark pedestal',
    'Precision raised table top', 'Precision table rail',
    'Precision table end stop', 'Raised copper workpiece',
    'Raised workpiece top plate', 'Precision clamp post',
    'Precision clamp arm', 'Precision clamp bolt', 'Precision table amber light',
)
table_parts = [o for o in scene.objects
               if any(o.name.startswith(p) for p in TABLE_PREFIXES)]
table_root = make_empty('RIG | rotary work table', (0, 0, 0), display=.16)
table_root.rotation_mode = 'XYZ'
for o in table_parts:
    attach_preserve_world(o, table_root)

# keyframe helpers
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Animated quality-flow ring: two warm comet arcs on the outer top rail.
# The rig turns 180 degrees per 32-frame cycle.  Because the two comets are
# 180 degrees apart, the final pose is visually identical to the first, so the
# stream loops seamlessly while each comet travels a half circle.
# ---------------------------------------------------------------------------
FLOW_MAT = bpy.data.materials.get('Glow | amber machining slot')
flow_rig = make_empty('RIG | flow ring', (0, 0, 0), display=.12)
flow_rig.rotation_mode = 'XYZ'
for comet in (0.0,):
    for k in range(24):
        ang = math.radians(comet - k * 2.20)
        radius = 1.405
        z = 1.318
        loc = (math.cos(ang) * radius, math.sin(ang) * radius, z)
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.object
        o.name = f'FLOW ring comet {int(comet)} part {k:02d}'
        o.dimensions = ((0.118 if k == 0 else 0.096), (0.036 if k < 8 else 0.030), 0.018)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        o.rotation_euler.z = ang + math.pi / 2
        o.data.materials.append(FLOW_MAT)
        attach_preserve_world(o, flow_rig)
        if k == 0:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6,
                                                 radius=.036, location=(loc[0], loc[1], z + .014))
            h = bpy.context.object
            h.name = f'FLOW ring comet {int(comet)} head glow'
            h.data.materials.append(FLOW_MAT)
            attach_preserve_world(h, flow_rig)

# One full lap per 32-frame cycle with an ease-in speed curve.  The small
# linear component keeps the comet moving at the start, then the power term
# makes each later part of the lap visibly faster.
for f in range(101, 133):
    t = (f - 101) / 31.0
    eased = 0.20 * t + 0.80 * (t ** 2.8)
    flow_rig.rotation_euler = (0, 0, math.radians(360.0 * eased))
    flow_rig.keyframe_insert('rotation_euler', frame=f, group=flow_rig.name)
if flow_rig.animation_data and flow_rig.animation_data.action:
    for fc in flow_rig.animation_data.action.fcurves:
        if fc.data_path == 'rotation_euler':
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'

def key_quat(empty, axis, degrees, frame):
    empty.rotation_quaternion = Quaternion(Vector(axis).normalized(),
                                           math.radians(degrees))
    empty.keyframe_insert('rotation_quaternion', frame=frame, group=empty.name)


def key_euler_y(empty, radians_value, frame):
    empty.rotation_euler = (0.0, radians_value, 0.0)
    empty.keyframe_insert('rotation_euler', frame=frame, group=empty.name)


def set_linear(empty, path='rotation_euler'):
    ad = empty.animation_data
    if not ad or not ad.action:
        return
    for fc in ad.action.fcurves:
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


# IDLE: 1..32, subtle servo breathing, slow internal watch-keeping.
IDLE_START, IDLE_END = 1, 32
for tag, rig in rigs.items():
    phase = math.radians(rig['phase'])
    for f in range(IDLE_START, IDLE_END + 1):
        t = (f - IDLE_START) / (IDLE_END - IDLE_START) * math.tau
        if tag.startswith('Left'):
            sh = 0.85 * math.sin(t + phase)
            el = 0.65 * math.sin(t + phase + 1.1)
            wr = 0.45 * math.sin(t + phase + 2.0)
        elif tag.startswith('Right'):
            sh = 0.55 * math.sin(t + phase + .6)
            el = 0.50 * math.sin(t + phase + 1.8)
            wr = 0.40 * math.sin(t + phase + 2.7)
        else:
            sh = 0.70 * math.sin(t + phase + .3)
            el = 0.95 * math.sin(t + phase + 1.9)
            wr = 0.55 * math.sin(t + phase + 2.4)
        orbit_yaw = 1.1 * math.sin(t + phase + .35)
        rig['orbit'].rotation_euler = (0, 0, math.radians(orbit_yaw))
        rig['orbit'].keyframe_insert('rotation_euler', frame=f, group=rig['orbit'].name)
        yaw = 1.4 * math.sin(t + phase + .7)
        rig['root'].rotation_euler = (0, 0, math.radians(yaw))
        rig['root'].keyframe_insert('rotation_euler', frame=f, group=rig['root'].name)
        key_quat(rig['shoulder'], rig['axis'], sh, f)
        key_quat(rig['elbow'], rig['axis'], el, f)
        key_quat(rig['wrist'], rig['axis'], wr, f)

# WORK: 101..132.  Two machining pulses per cycle, with a clear lift between
# them.  Signs are chosen per tangent axis so the tools dip toward the table.
WORK_START, WORK_END = 101, 132
motion_keys = [101, 106, 112, 120, 126, 132]

# Each arm has its own carriage on the circular rail.  They sweep short,
# independent arcs with different directions and timings instead of moving as
# one rigid carousel; all return to their starting station for a clean loop.
orbit_curves = {
    'Left primary manipulator':     [0, 6, 28, 34, 12, 0],
    'Right primary manipulator':    [0, -22, -12, 10, 26, 0],
    'Front auxiliary manipulator':  [0, 16, -10, -28, -8, 0],
}
for tag, angles in orbit_curves.items():
    rig = rigs[tag]
    for f, deg in zip(motion_keys, angles):
        rig['orbit'].rotation_euler = (0, 0, math.radians(deg))
        rig['orbit'].keyframe_insert('rotation_euler', frame=f, group=rig['orbit'].name)

# Safe pose while the carousel indexes: shoulder lifted, elbow folded.
# Working poses use the middle elbow joint for deep press/shear strokes.
safe = {'yaw': 0.0, 'sh': 16.0, 'el': 34.0, 'wr': -10.0}
poses = {
    'Left primary manipulator': [
        safe,
        safe,
        {'yaw': 15.0, 'sh': -27.0, 'el': -34.0, 'wr': 21.0},
        safe,
        safe,
        safe,
    ],
    'Right primary manipulator': [
        safe,
        safe,
        safe,
        safe,
        {'yaw': -14.0, 'sh': -29.0, 'el': -37.0, 'wr': 23.0},
        safe,
    ],
    'Front auxiliary manipulator': [
        safe,
        {'yaw': 22.0, 'sh': -14.0, 'el': -42.0, 'wr': 30.0},
        {'yaw': 26.0, 'sh': -18.0, 'el': -48.0, 'wr': 34.0},
        safe,
        {'yaw': -18.0, 'sh': -22.0, 'el': -38.0, 'wr': 24.0},
        safe,
    ],
}
for tag, curve in poses.items():
    rig = rigs[tag]
    for idx, f in enumerate(motion_keys):
        p = curve[idx]
        rig['root'].rotation_euler = (0, 0, math.radians(p['yaw']))
        rig['root'].keyframe_insert('rotation_euler', frame=f, group=rig['root'].name)
        key_quat(rig['shoulder'], rig['axis'], p['sh'], f)
        key_quat(rig['elbow'], rig['axis'], p['el'], f)
        key_quat(rig['wrist'], rig['axis'], p['wr'], f)

# Gears spin continuously through the working cycle; idle leaves them parked.
for rig, axis, speed in gear_rigs:
    for f, angle in ((WORK_START, 0.0), (111, math.pi * .5 * speed),
                     (121, math.pi * speed), (131, math.pi * 1.5 * speed),
                     (132, math.tau * speed)):
        key_euler_y(rig, angle, f)
    set_linear(rig)

# Table index sweep: two small opposing moves between the two machining
# strokes.  It returns to zero so the 32-frame cycle is seamless.
for f, degrees in ((101, 0), (109, 18), (117, -12), (125, 16), (132, 0)):
    table_root.rotation_euler = (0, 0, math.radians(degrees))
    table_root.keyframe_insert('rotation_euler', frame=f, group=table_root.name)
# idle table stays parked
for f in (1, 16, 32):
    table_root.rotation_euler = (0, 0, 0)
    table_root.keyframe_insert('rotation_euler', frame=f, group=table_root.name)

# Working chamber lights pulse with the two press strokes.
inside = bpy.data.objects.get('Warm chamber practical')
table_light = bpy.data.objects.get('Work-bed warm task light')
rim_light = bpy.data.objects.get('Chamber cool rim practical')
for light, values in (
    (inside, (95, 185, 265, 150, 275, 95)),
    (table_light, (85, 205, 305, 125, 315, 85)),
    (rim_light, (55, 90, 125, 75, 135, 55)),
):
    if light is None:
        continue
    for f, val in zip((101, 109, 113, 117, 125, 132), values):
        light.data.energy = val
        light.data.keyframe_insert('energy', frame=f, group=light.name)
# idle holds a low warm idle glow
for light, val in ((inside, 0), (table_light, 0), (rim_light, 0)):
    if light:
        for f in (1, 16, 32):
            light.data.energy = val
            light.data.keyframe_insert('energy', frame=f, group=light.name)

# Make the ranges obvious in the timeline.
scene.frame_start = 1
scene.frame_end = 132
scene['animation_ranges'] = {'idle': [1, 32], 'working': [101, 132]}

# A default camera framing for sprite export.  It is deliberately square and
# has the machine centred with room for the arm sweep.
cam = bpy.data.objects['Reference-match orthographic camera']
cam.data.ortho_scale = 4.95
cam.location = Vector((3.05, -7.35, 9.35))
cam.rotation_euler = (Vector((0, 0, .92)) - cam.location).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.wm.save_as_mainfile(filepath=str(DST))
print('Saved', DST)
print('Arm shrink', ARM_SHRINK, 'rigs', len(rigs), 'gears', len(gear_rigs))




