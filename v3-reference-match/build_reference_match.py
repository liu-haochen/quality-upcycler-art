"""Procedural Blender study matching the supplied v3/image.png reference.

The reference is a dense, weathered Factorio-style ring machine: a deep open
bowl, an uneven segmented rim, yellow manipulators, exposed pipes and a strong
sun shadow on a white field.  This script builds a new, fully procedural model
and renders a 2.86:1 presentation image in art/v3-reference-match/.
"""
import bpy
import math
import random
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent
random.seed(20261025)

# ---------------------------------------------------------------------------
# scene reset
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
              bpy.data.cameras, bpy.data.lights):
    # Do not purge materials that are still in use; a fresh background scene
    # has only the default material, so this is safe and keeps the file tidy.
    for item in list(block):
        if item.users == 0:
            block.remove(item)

# ---------------------------------------------------------------------------
# materials: old paint, cast iron, worn steel, copper, rubber and small glows
# ---------------------------------------------------------------------------
def make_metal(name, low, high, metallic, roughness, *, scale=3.0,
               detail=7.0, bump=0.020, edge=None, rust=None,
               rust_scale=8.0, rust_lo=0.46, rust_hi=0.72,
               emission=None, emission_strength=0.0, seed=0.0,
               bump_scale=55.0):
    """Layered procedural material.  Coordinates are object-local so every
    welded plate gets its own grime pattern without UV work."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    n = nt.nodes
    l = nt.links
    bsdf = n.get('Principled BSDF')
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness

    tc = n.new('ShaderNodeTexCoord')
    mp = n.new('ShaderNodeMapping')
    mp.inputs['Location'].default_value = (seed * 0.37, seed * 0.73, seed * 0.19)
    mp.inputs['Rotation'].default_value = (seed * 0.08, 0.0, seed * 0.11)
    l.new(tc.outputs['Object'], mp.inputs['Vector'])

    broad = n.new('ShaderNodeTexNoise')
    broad.inputs['Scale'].default_value = scale * 0.55
    broad.inputs['Detail'].default_value = detail
    broad.inputs['Roughness'].default_value = 0.68
    broad.inputs['Distortion'].default_value = 0.22
    l.new(mp.outputs['Vector'], broad.inputs['Vector'])

    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.34
    ramp.color_ramp.elements[0].color = (*low, 1)
    ramp.color_ramp.elements[1].position = 0.68
    ramp.color_ramp.elements[1].color = (*high, 1)
    l.new(broad.outputs['Fac'], ramp.inputs[0])

    base_socket = ramp.outputs[0]

    # Sparse rust/oxide islands.  A second noise keeps the edge irregular.
    if rust is not None:
        rn = n.new('ShaderNodeTexNoise')
        rn.inputs['Scale'].default_value = rust_scale
        rn.inputs['Detail'].default_value = 9.0
        rn.inputs['Roughness'].default_value = 0.78
        rn.inputs['Distortion'].default_value = 0.45
        l.new(mp.outputs['Vector'], rn.inputs['Vector'])
        rr = n.new('ShaderNodeValToRGB')
        rr.color_ramp.elements[0].position = rust_lo
        rr.color_ramp.elements[0].color = (0, 0, 0, 1)
        rr.color_ramp.elements[1].position = rust_hi
        rr.color_ramp.elements[1].color = (1, 1, 1, 1)
        l.new(rn.outputs['Fac'], rr.inputs[0])
        mixr = n.new('ShaderNodeMixRGB')
        mixr.blend_type = 'MIX'
        mixr.inputs[0].default_value = 1.0
        l.new(base_socket, mixr.inputs[1])
        mixr.inputs[2].default_value = (*rust, 1)
        l.new(rr.outputs[0], mixr.inputs[0])
        base_socket = mixr.outputs[0]

    # Convex bevels and rims catch bare metal / chipped paint.
    if edge is not None:
        geo = n.new('ShaderNodeNewGeometry')
        er = n.new('ShaderNodeValToRGB')
        er.color_ramp.elements[0].position = 0.43
        er.color_ramp.elements[0].color = (0, 0, 0, 1)
        er.color_ramp.elements[1].position = 0.68
        er.color_ramp.elements[1].color = (1, 1, 1, 1)
        l.new(geo.outputs['Pointiness'], er.inputs[0])
        mixe = n.new('ShaderNodeMixRGB')
        mixe.blend_type = 'MIX'
        mixe.inputs[0].default_value = 0.82
        l.new(base_socket, mixe.inputs[1])
        mixe.inputs[2].default_value = (*edge, 1)
        l.new(er.outputs[0], mixe.inputs[0])
        base_socket = mixe.outputs[0]

    # Cavity dirt / contact occlusion.
    ao = n.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = 0.22
    ao.samples = 8
    mixao = n.new('ShaderNodeMixRGB')
    mixao.blend_type = 'MULTIPLY'
    mixao.inputs[0].default_value = 0.60
    l.new(base_socket, mixao.inputs[1])
    l.new(ao.outputs['AO'], mixao.inputs[2])
    base_socket = mixao.outputs[0]
    l.new(base_socket, bsdf.inputs['Base Color'])

    # Roughness breakup, independent of diffuse colour.
    rrgh = n.new('ShaderNodeValToRGB')
    rrgh.color_ramp.elements[0].position = 0.18
    rrgh.color_ramp.elements[0].color = (max(0.02, roughness - 0.15),) * 3 + (1,)
    rrgh.color_ramp.elements[1].position = 0.86
    rrgh.color_ramp.elements[1].color = (min(1.0, roughness + 0.13),) * 3 + (1,)
    l.new(broad.outputs['Fac'], rrgh.inputs[0])
    l.new(rrgh.outputs[0], bsdf.inputs['Roughness'])

    # Fine hammered/pitted micro-bump plus broad surface undulation.
    micro = n.new('ShaderNodeTexNoise')
    micro.inputs['Scale'].default_value = bump_scale
    micro.inputs['Detail'].default_value = 4.0
    micro.inputs['Roughness'].default_value = 0.62
    l.new(mp.outputs['Vector'], micro.inputs['Vector'])
    bmp = n.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = max(0.045, bump * 1.65)
    bmp.inputs['Distance'].default_value = 0.013
    l.new(micro.outputs['Fac'], bmp.inputs['Height'])
    l.new(bmp.outputs[0], bsdf.inputs['Normal'])

    if emission is not None:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1)
        bsdf.inputs['Emission Strength'].default_value = emission_strength
    return m

# Four subtly different batches break the "all one clean material" look.
armor_a = make_metal('Armor | dirty teal steel', (.006,.010,.013), (.050,.085,.105),
                     .72, .55, edge=(.28,.42,.50), rust=(.085,.050,.025), seed=1.1)
armor_b = make_metal('Armor | blue grey plates', (.005,.008,.010), (.075,.105,.125),
                     .68, .56, edge=(.22,.33,.40), rust=(.080,.045,.022), seed=2.7)
armor_c = make_metal('Armor | pale silver blue covers', (.018,.026,.032), (.220,.270,.310),
                     .62, .48, edge=(.52,.62,.70), rust=(.090,.055,.030), seed=3.9)
armor_d = make_metal('Armor | dark teal rear castings', (.002,.004,.006), (.020,.035,.045),
                     .78, .62, edge=(.10,.18,.23), rust=(.045,.025,.012), seed=5.2)
steel = make_metal('Steel | cold worn machinery', (.030,.040,.050), (.300,.370,.430),
                   .94, .31, edge=(.58,.68,.75), rust=(.080,.050,.022),
                   scale=2.7, bump=.025, seed=7.0)
bare = make_metal('Steel | bright machined edges', (.100,.120,.140), (.600,.680,.750),
                  .97, .20, edge=(.85,.90,.95), rust=None, scale=2.1,
                  bump=.018, seed=8.1)
darkmetal = make_metal('Iron | black oiled recess', (.002,.004,.006), (.018,.030,.036),
                       .82, .52, edge=(.10,.15,.18), rust=(.040,.022,.008), seed=9.3)
rustmetal = make_metal('Iron | oxidised brown housings', (.020,.012,.007), (.110,.060,.025),
                       .58, .71, edge=(.22,.14,.07), rust=(.16,.08,.030),
                       scale=3.6, seed=10.7)
yellow = make_metal('Paint | brushed brass manipulator', (.035,.020,.003), (.58,.38,.085),
                    .74, .30, edge=(.92,.72,.28), rust=(.14,.08,.020),
                    scale=3.2, rust_lo=.52, rust_hi=.78, seed=12.5)
yellow2 = make_metal('Paint | dark bronze arm service pieces', (.025,.012,.002), (.24,.13,.018),
                     .70, .44, edge=(.50,.32,.08), rust=(.12,.07,.018), seed=13.9)
copper = make_metal('Copper | aged hydraulic lines', (.040,.012,.003), (.28,.09,.018),
                    .92, .36, edge=(.45,.22,.07), rust=(.045,.024,.010),
                    scale=5.2, bump=.018, seed=15.1)
red = make_metal('Paint | fire suppression red', (.025,.002,.0015), (.23,.012,.004),
                 .33, .60, edge=(.57,.14,.06), rust=(.13,.052,.012), seed=17.0)
rubber = make_metal('Rubber | black cable and seals', (.004,.0045,.004), (.022,.023,.020),
                    .04, .79, scale=4.5, bump=.05, seed=18.2, bump_scale=110)
brass = make_metal('Brass | small worn fittings', (.060,.030,.008), (.38,.20,.045),
                   .92, .30, edge=(.80,.61,.20), rust=(.14,.07,.018), seed=19.4)
bluepipe = make_metal('Paint | blue grey coolant pipe', (.015,.040,.045), (.080,.220,.250),
                      .72, .42, edge=(.25,.50,.55), rust=(.045,.035,.020),
                      scale=4.5, seed=19.8)
teal = make_metal('Paint | oxidised teal fittings', (.008,.050,.045), (.040,.220,.180),
                  .60, .64, edge=(.15,.50,.42), rust=(.08,.04,.015), seed=20.6)
oxidized = make_metal('Copper | green oxidised fittings', (.030,.055,.035), (.12,.25,.16),
                      .50, .72, edge=(.32,.46,.30), rust=(.18,.10,.035), seed=21.4)
label = make_metal('Labels | dirty cool white decals', (.120,.140,.150), (.550,.620,.660),
                   .20, .56, scale=5.0, bump=.008, seed=20.2)

brightsteel = make_metal('Steel | bright work-bed surfaces', (.100,.130,.150), (.550,.640,.720),
                         .95, .22, edge=(.82,.88,.94), rust=(.09,.05,.020),
                         scale=2.0, bump=.015, seed=24.8)
glow_orange = make_metal('Glow | amber machining slot', (.45,.035,.003), (1.0,.15,.01),
                         .1, .35, emission=(1.0,.10,.006), emission_strength=7.0,
                         seed=21.0, bump=.005)
glow_green = make_metal('Glow | green diagnostics', (.006,.10,.065), (.035,.48,.24),
                        .12, .42, emission=(.025,.50,.20), emission_strength=1.35,
                        seed=22.0, bump=.005)
glow_red = make_metal('Glow | red indicators', (.40,.005,.003), (1.0,.04,.01),
                      .1, .35, emission=(1.0,.025,.006), emission_strength=4.0,
                      seed=23.0, bump=.005)
quality_uncommon = make_metal('Glow | quality uncommon', (.002,.075,.018), (.030,.38,.070),
                             .20, .36, emission=(.04,.62,.14), emission_strength=1.15,
                             seed=31.0, bump=.004)
quality_rare = make_metal('Glow | quality rare', (.002,.025,.085), (.020,.12,.40),
                          .20, .34, emission=(.035,.18,.62), emission_strength=1.15,
                          seed=32.0, bump=.004)
quality_epic = make_metal('Glow | quality epic', (.045,.008,.095), (.18,.040,.32),
                          .20, .34, emission=(.32,.07,.52), emission_strength=1.15,
                          seed=33.0, bump=.004)
quality_legendary = make_metal('Glow | quality legendary', (.09,.030,.002), (.38,.14,.018),
                               .20, .32, emission=(.68,.27,.030), emission_strength=1.25,
                               seed=34.0, bump=.004)
quality_mats = (quality_uncommon, quality_rare, quality_epic, quality_legendary)

white_metal = make_metal('White | ceramic insulators', (.22,.22,.20), (.72,.70,.62),
                         .08, .42, edge=(.85,.83,.72), seed=24.0)

# ---------------------------------------------------------------------------
# primitive helpers
# ---------------------------------------------------------------------------
def finish(o, name, mat, bevel=0.010, smooth=False):
    o.name = name
    if mat is not None:
        o.data.materials.append(mat)
    if bevel:
        b = o.modifiers.new('soft worn edges', 'BEVEL')
        b.width = bevel
        b.segments = 2
        b.limit_method = 'ANGLE'
        b.angle_limit = math.radians(38)
        o.modifiers.new('weighted normals', 'WEIGHTED_NORMAL')
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    return o


def box(name, loc, size, mat, bevel=0.012, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.rotation_euler = rot
    return finish(o, name, mat, bevel)


def cyl(name, loc, radius, depth, mat, axis=(0, 0, 1), verts=28, bevel=0.006):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=depth, location=loc)
    o = bpy.context.object
    o.rotation_euler = Vector(axis).to_track_quat('Z', 'Y').to_euler()
    return finish(o, name, mat, bevel, smooth=True)


def rod(name, a, b, radius, mat, verts=20, bevel=0.004):
    a = Vector(a); b = Vector(b)
    return cyl(name, (a + b) * .5, radius, (b - a).length, mat,
               axis=(b - a), verts=verts, bevel=bevel)


def beam(name, a, b, width, depth, mat, bevel=0.012):
    a = Vector(a); b = Vector(b)
    o = box(name, (a + b) * .5, (width, depth, (b - a).length), mat, bevel)
    o.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    return o


def tube(name, points, radius, mat, resolution=4, bevel_res=3):
    c = bpy.data.curves.new(name, 'CURVE')
    c.dimensions = '3D'
    c.resolution_u = resolution
    c.bevel_depth = radius
    c.bevel_resolution = bevel_res
    c.fill_mode = 'FULL'
    s = c.splines.new('BEZIER')
    s.bezier_points.add(len(points) - 1)
    for p, co in zip(s.bezier_points, points):
        p.co = co
        p.handle_left_type = 'AUTO'
        p.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, c)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def arc_slab(name, ri, ro, z0, z1, a0, a1, mat, steps=None, bevel=.008):
    """Closed annular wedge with top, bottom, inner and outer walls."""
    if steps is None:
        steps = max(2, int(abs(a1 - a0) / 5))
    n = steps + 1
    verts = []
    def pol(r, a, z):
        a = math.radians(a)
        return (r * math.cos(a), r * math.sin(a), z)
    for z in (z0, z1):
        for r in (ri, ro):
            verts.extend(pol(r, a0 + (a1 - a0) * i / steps, z) for i in range(n))
    faces = []
    for i in range(steps):
        faces.extend([
            (i, i + 1, n + i + 1, n + i),
            (2 * n + i, 3 * n + i, 3 * n + i + 1, 2 * n + i + 1),
            (i, 2 * n + i, 2 * n + i + 1, i + 1),
            (n + i, n + i + 1, 3 * n + i + 1, 3 * n + i),
        ])
    faces.extend([(0, n, 3 * n, 2 * n),
                  (steps, 2 * n + steps, 3 * n + steps, n + steps)])
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return finish(o, name, mat, bevel)


def ring_band(name, ri, ro, z0, z1, mat, segments=96, bevel=.008):
    return arc_slab(name, ri, ro, z0, z1, 0, 360, mat, steps=segments, bevel=bevel)


def torus(name, loc, major, minor, mat, major_seg=64, minor_seg=8):
    bpy.ops.mesh.primitive_torus_add(location=loc, major_radius=major,
                                     minor_radius=minor,
                                     major_segments=major_seg,
                                     minor_segments=minor_seg)
    return finish(bpy.context.object, name, mat, 0, smooth=True)


def polar(r, a, z=0.0):
    a = math.radians(a)
    return Vector((r * math.cos(a), r * math.sin(a), z))


def bolt(name, p, normal, radius=.025, depth=.018, mat=steel):
    p = Vector(p)
    return cyl(name, p, radius, depth, mat, axis=Vector(normal), verts=10, bevel=.002)


def bolt_arc(prefix, r, z, a0, a1, count, normal='radial', radius=.021):
    for i in range(count):
        a = a0 + (a1 - a0) * i / max(1, count - 1)
        p = polar(r, a, z)
        n = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        if normal == 'up':
            n = Vector((0, 0, 1))
        bolt(f'{prefix} {i:02d}', p, n, radius=radius)


# ---------------------------------------------------------------------------
def gear(name, center, radius, depth, teeth, mat, axis=(0, 0, 1)):
    c = Vector(center)
    axis = Vector(axis).normalized()
    cyl(name + ' web', c, radius * .70, depth, mat, axis=axis, verts=24)
    for i in range(teeth):
        a = i * 360 / teeth
        q = c + Vector((math.cos(math.radians(a)) * radius,
                        math.sin(math.radians(a)) * radius, 0))
        o = box(name + f' tooth {i:02d}', q, (.050, .036, depth * .86),
                mat, .003)
        o.rotation_euler.z = math.radians(a + 90)
    bolt(name + ' axle', c, axis, radius * .19, depth * 1.35, bare)

# heavy circular body / skirt
# ---------------------------------------------------------------------------
base_z = 0.12
# broad bottom casting, slightly ellipse-shaped by attachments later
cyl('Black circular foundation', (0, 0, 0.09), 1.62, 0.18, darkmetal, verts=96)
ring_band('Heavy lower skirt', 1.43, 1.57, .20, .58, armor_d, segments=96, bevel=.010)
# hollow upper shell; the processing chamber must stay open, not capped by the body
ring_band('Tapered load-bearing outer shell', 1.45, 1.57, .58, .775, armor_a, segments=96, bevel=.012)







# outer lower and upper belts
ring_band('Lower dark belt', 1.57, 1.63, .235, .285, darkmetal, segments=96, bevel=.009)
ring_band('Mid grey belt', 1.56, 1.645, .54, .605, armor_c, segments=96, bevel=.010)
ring_band('Upper dark belt', 1.46, 1.54, .76, .815, rustmetal, segments=96, bevel=.008)

# individual curved side plates with tiny gaps; variation keeps the barrel
# from reading as a clean extrusion.
plate_mats = [armor_a, armor_b, bluepipe, armor_c, armor_a, armor_d,
              armor_b, teal, armor_c, armor_b, bluepipe, armor_d]
for i in range(18):
    a0 = -90 + i * 20 + 0.75
    a1 = a0 + 18.4
    m = plate_mats[i % len(plate_mats)]
    arc_slab(f'Curved body armour {i:02d}', 1.555, 1.61, .30, .72,
             a0, a1, m, steps=6, bevel=.010)
    # vertical strap at each plate seam
    a = a0 - 0.5
    p = polar(1.615, a, .51)
    o = box(f'Body seam strap {i:02d}', p, (.055, .085, .42), darkmetal, .008)
    o.rotation_euler.z = math.radians(a)
    bolt(f'Body strap bolt {i:02d}', polar(1.66, a, .69), (math.cos(math.radians(a)),
         math.sin(math.radians(a)), 0), .022, .02)

# horizontal reinforcing band around the body, raised in a few places
for a0, a1, m in [(-172, -92, armor_c), (-82, -8, armor_c), (4, 55, darkmetal),
                  (62, 118, armor_b), (126, 168, armor_c)]:
    arc_slab('Bolted horizontal repair rail', 1.61, 1.655, .395, .455,
             a0, a1, m, steps=max(4, int((a1 - a0) / 5)), bevel=.008)
    for j in range(max(2, int((a1 - a0) / 20))):
        aa = a0 + (a1 - a0) * (j + .5) / max(2, int((a1 - a0) / 20))
        bolt('Repair rail rivet', polar(1.67, aa, .425),
             Vector((math.cos(math.radians(aa)), math.sin(math.radians(aa)), 0)),
             .018, .018, bare)

# Large overlapping armor plates around the body.  These broader shapes are
# what give the reference its armored, repaired look instead of a stack of
# narrow horizontal bands.
large_body_panels = [
    (-166, 27, .29, .30, armor_c), (-134, 25, .38, .34, bluepipe),
    (-106, 30, .28, .36, steel),   (-78, 27, .40, .32, armor_a),
    (-50, 31, .31, .27, rustmetal), (-18, 27, .42, .34, armor_c),
    (18, 23, .33, .30, armor_b),    (62, 25, .37, .32, teal),
    (104, 21, .29, .28, armor_a),   (142, 24, .36, .31, steel),
]
for i, (a0, span, z0, h, mat) in enumerate(large_body_panels):
    arc_slab(f'Large layered body armor {i:02d}', 1.625, 1.690,
             z0, z0 + h, a0, a0 + span, mat, steps=7, bevel=.014)
    arc_slab(f'Large armor dark lower shadow {i:02d}', 1.681, 1.700,
             z0 - .018, z0 + .012, a0 + .7, a0 + span - .7,
             darkmetal, steps=5, bevel=.004)
    # two rows of heavy fasteners
    for aa in (a0 + 2.1, a0 + span - 2.1):
        for zz in (z0 + .045, z0 + h - .045):
            bolt(f'Large armor bolt {i:02d}.{aa:.0f}.{zz:.2f}',
                 polar(1.708, aa, zz),
                 Vector((math.cos(math.radians(aa)), math.sin(math.radians(aa)), 0)),
                 .024, .018, bare)
    # service handle / lifting lug in the middle
    pc = polar(1.715, a0 + span * .5, z0 + h * .52)
    box(f'Large armor lifting lug {i:02d}', pc, (.075, .025, .12),
        darkmetal, .006, rot=(0, 0, math.radians(a0 + span * .5 + 90)))
    if i % 2 == 0:
        arc_slab(f'Large armor oxidised streak {i:02d}', 1.690, 1.702,
                 z0 + .03, z0 + h * .68, a0 + span * .22, a0 + span * .46,
                 rustmetal, steps=4, bevel=.002)

# Front access plate and a wide warm inspection slot, like the amber window
# across the front of the reference machine.
front_a = -90
p = polar(1.635, front_a, .42)
front = box('Front lower access hatch', p, (.68, .085, .30), darkmetal, .012,
            rot=(0, 0, math.radians(front_a + 90)))
box('Front hatch inset', polar(1.686, front_a, .42), (.56, .035, .20),
    armor_b, .008, rot=(0, 0, math.radians(front_a + 90)))
box('Amber inspection window', polar(1.710, front_a, .47), (.38, .020, .080),
    glow_orange, .006, rot=(0, 0, math.radians(front_a + 90)))
box('Amber window lower frame', polar(1.704, front_a, .405), (.43, .024, .035),
    darkmetal, .004, rot=(0, 0, math.radians(front_a + 90)))
# caution stripes beside the window, now on the actual front face
for k in range(7):
    x = -.27 + k * .090
    pstripe = (x, -1.625, .58)
    o = box('Caution stripe', pstripe, (.042, .018, .060), yellow2 if k % 2 else darkmetal, .003,
            rot=(0, 0, 0))

# ---------------------------------------------------------------------------
# outer rim / multi-layer rotating ring
# ---------------------------------------------------------------------------
# dark inner collar and mechanical well
ring_band('Upper collar casting', .985, 1.46, .715, .895, darkmetal, segments=96, bevel=.012)
ring_band('Collar top worn rail', 1.36, 1.48, .89, .94, steel, segments=96, bevel=.008)
ring_band('Deep well outer wall', .920, .985, .24, .88, armor_d, segments=96, bevel=.010)
# inner vertical ribs, alternating rust and black iron
for i in range(24):
    a = i * 15
    o = box(f'Inner well rib {i:02d}', polar(.925, a, .60),
            (.065, .09, .55), rustmetal if i % 4 else darkmetal, .007)
    o.rotation_euler.z = math.radians(a)
# dark bottom chamber disk
cyl('Chamber lower floor', (0, 0, .285), .94, .10, darkmetal, verts=96)

# heavy shadowed under-rim so the ring assembly has real mass
ring_band('Heavy under-rim casting', 1.43, 1.57, .825, .925, armor_d, segments=96, bevel=.012)
ring_band('Outer rusted under-rim band', 1.50, 1.60, .855, .905, rustmetal, segments=96, bevel=.008)
for i in range(18):
    a = i * 20 + 10
    o = box('Outer under-rim clamp', polar(1.56, a, .875), (.09, .08, .10),
            darkmetal, .006, rot=(0, 0, math.radians(a)))
    bolt('Outer under-rim bolt', polar(1.60, a, .90),
         (math.cos(math.radians(a)), math.sin(math.radians(a)), 0),
         .018, .014, bare)

# Heavy segmented rim: the reference reads as bolted, repairable castings
# rather than a polished machined torus.
for i in range(12):
    a0 = i * 30 + .8
    a1 = a0 + 28.4
    m = [rustmetal, armor_b, darkmetal, bluepipe, armor_c, armor_b,
         rustmetal, steel, armor_b, rustmetal, armor_c, teal][i % 12]
    arc_slab(f'Outer segmented rim {i:02d}', 1.22, 1.49, .905, 1.035,
             a0, a1, m, steps=7, bevel=.015)
    # a dark, worn chipped top cap on every second segment
    if i % 2 == 0:
        arc_slab(f'Rim top replacement cap {i:02d}', 1.27, 1.44, 1.035, 1.060,
                 a0 + 1.4, a1 - 1.4, rustmetal if i % 4 else darkmetal,
                 steps=5, bevel=.007)
    arc_slab(f'Rim lower guard lip {i:02d}', 1.16, 1.30, .86, .925,
             a0 + .5, a1 - .5, armor_d, steps=5, bevel=.009)
    # chunky fasteners and small cast bosses at both ends
    for aa in (a0 + 1.2, a1 - 1.2):
        bolt(f'Rim segment bolt {i:02d}', polar(1.34, aa, 1.064),
             (0, 0, 1), .030, .027, bare)
        cyl(f'Rim cast boss {i:02d}', polar(1.41, aa, .96), .050, .04,
            armor_b, verts=12)
    # dark roller blocks visible through gaps
    a = a0 + 14
    box(f'Rim roller block {i:02d}', polar(1.155, a, .955),
        (.115, .055, .085), darkmetal, .005,
        rot=(0, 0, math.radians(a)))

# Inner rotary bearing track and tooth ring.
ring_band('Bearing track outer', 1.070, 1.165, .965, 1.018, darkmetal, segments=96, bevel=.007)
ring_band('Bearing track inner', .985, 1.060, .975, 1.038, steel, segments=96, bevel=.005)
for i in range(52):
    a = i * 360 / 52
    o = box(f'Rotary bearing tooth {i:02d}', polar(1.035, a, 1.027),
            (.050, .026, .038), bare if i % 6 else steel, .003)
    o.rotation_euler.z = math.radians(a + 90)
    if i % 3 == 0:
        bolt(f'Bearing tooth bolt {i:02d}', polar(1.14, a, 1.045),
             (0, 0, 1), .012, .010, bare)

# bright outer top lip and dense replaceable lugs: the reference's rim has a
# strong silvery read, interrupted by rust, bolts and maintenance tabs
for i in range(10):
    a0 = i * 36 + 1.3
    a1 = a0 + 33.4
    lip_mat = [steel, armor_c, darkmetal, steel, rustmetal,
               armor_c, steel, armor_b, steel, rustmetal][i]
    arc_slab(f'Bright outer rim lip {i:02d}', 1.335, 1.492, 1.040, 1.078,
             a0, a1, lip_mat, steps=6, bevel=.009)
    for aa in (a0 + 2.5, a1 - 2.5):
        bolt(f'Rim lip bolt {i:02d}.{aa:.0f}', polar(1.42, aa, 1.087),
             (0, 0, 1), .022, .018, bare)
for i in range(36):
    a = i * 10 + 4
    mat = [steel, armor_c, darkmetal, rustmetal][i % 4]
    o = box(f'Rim replaceable lug {i:02d}', polar(1.405, a, 1.092),
            (.090, .055, .028), mat, .004,
            rot=(0, 0, math.radians(a + 90)))
    bolt(f'Rim lug fastener {i:02d}', polar(1.405, a, 1.108),
         (0, 0, 1), .012, .010, bare)
# narrow dark groove under the lip
ring_band('Dark groove under outer lip', 1.330, 1.502, 1.026, 1.042,
          darkmetal, segments=96, bevel=.004)

# Two thick, worn concentric rails and twelve heavy radial bridge plates.
for r, z, rad, mat in [(1.50, 1.042, .034, steel),
                       (1.21, 1.065, .027, rustmetal),
                       (1.10, 1.018, .018, darkmetal)]:
    steps = 128
    pts = [polar(r, i * 360 / steps, z) for i in range(steps + 1)]
    tube('Thick worn rim rail', pts, rad, mat, resolution=2, bevel_res=2)
for i in range(12):
    a = i * 30 + 15
    p0 = polar(1.05, a, 1.055)
    p1 = polar(1.47, a, 1.045)
    beam(f'Rim radial bridge {i:02d}', p0, p1, .085, .062,
         armor_c if i % 3 else steel, .010)
    o = box(f'Rim bridge wear pad {i:02d}', polar(1.34, a, 1.075),
            (.24, .14, .042), darkmetal if i % 2 else rustmetal, .007)
    o.rotation_euler.z = math.radians(a + 90)
    bolt(f'Rim bridge fastener {i:02d}', p1 + Vector((0, 0, .025)),
         (0, 0, 1), .022, .018, bare)
    # clamp block hugging the outer rail
    q = polar(1.49, a, 1.01)
    box(f'Outer rail clamp {i:02d}', q, (.11, .075, .12), darkmetal, .006,
        rot=(0, 0, math.radians(a)))

# lower vertical supports around the body
for i in range(12):
    a = i * 30
    rod(f'Rim support stanchion {i:02d}', polar(1.36, a, .70),
        polar(1.36, a, .94), .045, darkmetal)
    cylinder = cyl(f'Stanchion foot {i:02d}', polar(1.37, a, .70),
                   .062, .045, steel, verts=12)

# ---------------------------------------------------------------------------
# inner floor, rotary table, fixture and workpieces
# ---------------------------------------------------------------------------
# slightly raised circular lower well floor
# Deep, dirty bowl and a clearly defined machine table inside it.
cyl('Inner lower well shadow plate', (0, 0, .335), .91, .055, darkmetal, verts=64)
cyl('Inner recessed dirty floor', (0, 0, .365), .80, .030, rustmetal, verts=64)
cyl('Inner floor centre oil pool', (0, 0, .383), .63, .012, darkmetal, verts=64)
# Insides of the well get their own ribbed, patched wall.  This is the dark
# brown band visible behind the table in the reference.
for i in range(16):
    a0 = i * 22.5 + .8
    a1 = a0 + 21.0
    arc_slab(f'Inner well lining plate {i:02d}', .885, .955, .39, .83,
             a0, a1, [rustmetal, armor_b, armor_d, steel][i % 4],
             steps=5, bevel=.006)
for z in (.50, .67, .80):
    ring_band('Inner well horizontal rib', .90, .935, z, z + .035,
              darkmetal, segments=96, bevel=.004)
for i in range(10):
    a = i * 36 + 18
    p = polar(.89, a, .59)
    box(f'Inner wall vertical rib {i:02d}', p, (.045, .06, .40), steel, .005,
        rot=(0, 0, math.radians(a)))
    if i % 3 == 0:
        bolt(f'Inner wall rib bolt {i:02d}', polar(.925, a, .79), (0, 0, 1),
             .014, .012, bare)
# warm ring of deposits / reflected copper at the back
for i in range(22):
    a = 4 + i * 16.36
    o = box(f'Interior brass deposit {i:02d}', polar(.72, a, .397),
            (.13, .055, .016), copper if i % 3 else brass, .003)
    o.rotation_euler.z = math.radians(a + 90)
# interior overhead lamp hoods (the reference has warm amber glints)
for a in (105, 150, 215):
    p = polar(.72, a, .86)
    box(f'Interior lamp hood {a}', p, (.18, .10, .09), darkmetal, .008,
        rot=(0, 0, math.radians(a)))
    q = polar(.69, a, .81)
    box(f'Interior amber lamp {a}', q, (.14, .05, .025), glow_orange, .004,
        rot=(0, 0, math.radians(a)))

# Heavy rotary index platter.
cyl('Rotary index platter', (0, 0, .405), .51, .075, darkmetal, verts=64)
cyl('Rotary platter machined top', (0, 0, .452), .455, .022, steel, verts=64)
ring_band('Rotary platter outer lip', .455, .515, .438, .480, bare, segments=64, bevel=.007)
ring_band('Rotary platter lower rim', .505, .565, .395, .440, rustmetal, segments=64, bevel=.007)
for i in range(10):
    a = i * 36 + 18
    o = box(f'Platter index tooth {i:02d}', polar(.52, a, .448),
            (.085, .038, .026), steel, .003)
    o.rotation_euler.z = math.radians(a)
    bolt(f'Platter tooth bolt {i:02d}', polar(.455, a, .475), (0, 0, 1),
         .012, .010, bare)

# Central work bed, clamps and visible machined workpiece.  Make this the
# brightest precision object in the otherwise dark bowl.
box('Central machining bed', (0, .03, .505), (.76, .52, .10), rustmetal, .014)
box('Central bed bright top', (0, .03, .558), (.64, .40, .030), brightsteel, .009)
for x in (-.27, .26):
    box('Bed edge rail', (x, .03, .585), (.055, .43, .060), steel, .007)
for y in (-.21, .22):
    box('Bed end rail', (0, y, .585), (.69, .045, .055), darkmetal, .006)
box('Central fixed jaw', (-.23, .01, .616), (.12, .44, .13), darkmetal, .011)
box('Central sliding jaw', (.22, -.015, .612), (.15, .35, .12), armor_c, .010)
box('Jaw clamp wedge', (.09, -.02, .628), (.12, .19, .085), steel, .007,
    rot=(0, 0, math.radians(8)))
# workpiece + clamp towers
box('Clamped steel workpiece', (-.015, .01, .674), (.31, .22, .065), copper, .008)
box('Workpiece upper plate', (-.015, .01, .713), (.22, .15, .028), brightsteel, .005)
for x in (-.17, .13):
    cyl('Clamp pressure cylinder', (x, .02, .69), .042, .12, steel, verts=16)
    cyl('Clamp dark cap', (x, .02, .758), .031, .025, darkmetal, verts=16)
    cyl('Clamp brass nut', (x, .02, .74), .05, .022, brass, verts=6)
# front vise body and adjustment wheel
box('Front vise body', (-.31, -.31, .535), (.25, .16, .14), armor_b, .010,
    rot=(0, 0, math.radians(-18)))
cyl('Vise adjustment wheel', (-.45, -.34, .55), .085, .035, rustmetal,
    axis=(0, 1, 0), verts=20)
cyl('Vise wheel hub', (-.45, -.365, .55), .035, .025, bare,
    axis=(0, 1, 0), verts=12)
# exposed gear train at the rear and side of the bowl
gear('Rear internal reduction gear', (0, .46, .54), .24, .09, 18, rustmetal,
     axis=(0, 1, 0))
gear('Rear internal pinion', (.32, .34, .51), .13, .075, 12, steel,
     axis=(0, 1, 0))
cyl('Rear chamber spindle', (0, .40, .52), .085, .22, bare,
    axis=(0, 1, 0), verts=24)
for i in range(9):
    a = 145 + i * 20
    o = box(f'Rear chamber heat exchanger fin {i:02d}', polar(.76, a, .50),
            (.17, .04, .13), rustmetal if i % 2 else darkmetal, .004)
    o.rotation_euler.z = math.radians(a + 90)
# gantry pillars + cross bar inside the back of the well
for x in (-.52, .52):
    box('Inner gantry pillar', (x, .34, .73), (.075, .11, .42), armor_b, .007)
beam('Inner gantry crossbar', (-.52, .34, .92), (.52, .34, .92),
     .105, .10, darkmetal, .008)
for x in (-.35, -.1, .15, .4):
    box('Gantry hanging clamp', (x, .34, .84), (.045, .06, .13), steel, .004)
# dangling hoses and power cables in the bowl
for k in range(6):
    a = 35 + k * 48
    tube(f'Inner chamber cable {k}',
         [polar(.78, a, .44), polar(.85, a + 5, .58), polar(.66, a + 3, .72),
          polar(.45, a - 2, .66)], .010 if k % 2 else .014,
         copper if k % 2 else rubber, resolution=4)
# a few small amber hot-spots down in the works
for i, (a, z, size) in enumerate([(115, .47, (.25, .03, .06)),
                                  (235, .45, (.18, .025, .045)),
                                  (22, .44, (.15, .025, .035))]):
    p = polar(.79, a, z)
    o = box(f'Chamber amber glimmer {i}', p, size, glow_orange, .006)
    o.rotation_euler.z = math.radians(a + 90)

# ---------------------------------------------------------------------------
# Raised precision table / workpiece stack: a bright, readable island in the
# deep chamber, corresponding to the rectangular fixture in the reference.
box('Precision table dark pedestal', (-.04, -.09, .585), (.74, .50, .11),
    armor_d, .010)
box('Precision raised table top', (-.04, -.09, .646), (.80, .55, .050),
    brightsteel, .010)
for x in (-.36, .28):
    box('Precision table rail', (x, -.09, .676), (.055, .54, .045), steel, .005)
for y in (-.34, .16):
    box('Precision table end stop', (-.04, y, .676), (.75, .045, .045),
        darkmetal, .005)
box('Raised copper workpiece', (-.02, -.10, .714), (.35, .26, .075), copper, .009)
box('Raised workpiece top plate', (-.02, -.10, .760), (.26, .18, .025),
    brightsteel, .004)
for x, y in [(-.23, -.23), (.18, -.23), (-.23, .03), (.18, .03)]:
    cyl('Precision clamp post', (x, y, .716), .034, .11, steel, verts=12)
    beam('Precision clamp arm', (x, y, .768), (x * .62, y * .70, .748),
         .050, .050, darkmetal, .004)
    bolt('Precision clamp bolt', (x, y, .785), (0, 0, 1), .018, .014, bare)
box('Precision table amber light', (-.04, -.38, .620), (.56, .018, .030),
    glow_orange, .004)
# heavy inner-wall conduit, controls and hanging hoses
for a in (74, 94, 116, 154, 206, 246):
    p = polar(.875, a, .62)
    box(f'Inner wall control box {a}', p, (.16, .06, .16), darkmetal, .006,
        rot=(0, 0, math.radians(a + 90)))
    box(f'Inner wall control label {a}', p + polar(.04, a, 0),
        (.10, .012, .055), label, .002,
        rot=(0, 0, math.radians(a + 90)))
    if a % 2 == 0:
        cyl(f'Inner wall red beacon {a}', p + Vector((0, 0, .08)), .018, .020,
            glow_red, axis=(math.cos(math.radians(a)), math.sin(math.radians(a)), 0),
            verts=10)
for a0, a1, z in [(64, 142, .73), (218, 292, .68), (112, 172, .47)]:
    pts = [polar(.89, a0 + (a1 - a0) * i / 18, z + .02 * math.sin(i * 1.1))
           for i in range(19)]
    tube('Inner wall copper manifold', pts, .018, copper, resolution=4)
# hanging conduits from the gantry down toward the table
for k, (x, y) in enumerate([(-.34, .14), (.33, .16), (.12, .30), (-.10, .27)]):
    tube(f'Overhead hanging conduit {k}',
         [(x, y, .92), (x * 1.15, y + .06, .78), (x * .80, y - .04, .62),
          (x * .45, y - .12, .54)], .013 if k % 2 else .019,
         rubber if k % 3 else copper, resolution=4)
    cyl(f'Overhead conduit socket {k}', (x, y, .915), .035, .045,
        darkmetal, verts=12)

# yellow manipulators (3 large + one small service arm)
# ---------------------------------------------------------------------------
def arm_joint(name, p, axis, size=1.0, mat_joint=darkmetal, mat_cap=steel):
    p = Vector(p)
    cyl(name + ' dark hub', p, .085 * size, .20 * size, mat_joint,
        axis=axis, verts=20, bevel=.004)
    cyl(name + ' steel cap', p + Vector(axis).normalized() * (.11 * size),
        .054 * size, .022 * size, mat_cap, axis=axis, verts=16, bevel=.003)


def build_arm(tag, base_a, shoulder_z, elbow, wrist, tool_tip, scale=1.0):
    elbow = Vector(elbow); wrist = Vector(wrist); tool_tip = Vector(tool_tip)
    axis = Vector((-math.sin(math.radians(base_a)),
                   math.cos(math.radians(base_a)), 0))
    base = polar(1.17, base_a, .99)
    shoulder = base + Vector((0, 0, shoulder_z))
    # ring-mounted azimuth bearing
    cyl(tag + ' base bearing', base, .205 * scale, .13, darkmetal, verts=28)
    cyl(tag + ' base ring', base + Vector((0, 0, .075)), .175 * scale, .070,
        steel, verts=28)
    cyl(tag + ' shoulder housing', shoulder, .238 * scale, .32 * scale,
        yellow2, axis=axis, verts=24)
    box(tag + ' shoulder block',
        shoulder + Vector((0, 0, .08)),
        (.32 * scale, .38 * scale, .25 * scale), yellow, .025,
        rot=(0, 0, math.radians(base_a + 90)))
    arm_joint(tag + ' shoulder', shoulder, axis, 2.10 * scale)
    # chunky, layered yellow upper arm with dark mechanical seams
    beam(tag + ' upper arm', shoulder, elbow, .365 * scale, .445 * scale,
         yellow, .032)
    for side in (-1, 1):
        q = (shoulder + elbow) * .5 + axis * (.17 * scale * side)
        o = box(tag + ' upper arm cheek plate', q,
                (.145 * scale, .225 * scale, .30 * scale), yellow2, .015)
        o.rotation_euler = (elbow - shoulder).to_track_quat('Z', 'Y').to_euler()
        bolt(tag + ' upper arm cheek bolt',
             q + (elbow - shoulder).normalized() * .09, axis,
             .020, .014, bare)
    box(tag + ' upper arm dark spine',
        (shoulder + elbow) * .5 - axis * (.145 * scale),
        (.070, .135 * scale, .34 * scale), darkmetal, .009,
        rot=(elbow - shoulder).to_track_quat('Z', 'Y').to_euler())
    # dark wrapped seams break up the large yellow castings
    for band_i, frac in enumerate((.22, .50, .78)):
        q = shoulder.lerp(elbow, frac)
        band = box(tag + f' upper arm dark wrap {band_i}', q,
                   (.445 * scale, .520 * scale, .075 * scale),
                   darkmetal, .010,
                   rot=(elbow - shoulder).to_track_quat('Z', 'Y').to_euler())
        bolt(tag + f' arm wrap bolt {band_i}', q + axis * (.25 * scale),
             axis, .022, .018, bare)
    tube(tag + ' arm loose loom',
         [shoulder + axis * (.12 * scale), shoulder.lerp(elbow, .35) + axis * (.23 * scale),
          elbow.lerp(wrist, .28) + axis * (.20 * scale), wrist + axis * (.11 * scale)],
         .018, rubber, resolution=5)
    arm_joint(tag + ' elbow', elbow, axis, 1.94 * scale)
    # visible hydraulic ram behind the upper arm
    p0 = shoulder + Vector((0, 0, .14)) - axis * (.17 * scale)
    p1 = elbow + Vector((0, 0, -.07)) - axis * (.19 * scale)
    rod(tag + ' hydraulic barrel', p0, p1, .055 * scale, darkmetal)
    rod(tag + ' hydraulic piston', p0.lerp(p1, .50), p1, .030 * scale, bare)
    cyl(tag + ' hydraulic gland', p0.lerp(p1, .50), .067 * scale, .055,
        brass, axis=(p1 - p0), verts=16)
    # forearm: darker slimmer body inside armored yellow guards
    beam(tag + ' forearm', elbow, wrist, .278 * scale, .330 * scale,
         yellow2, .025)
    box(tag + ' forearm dark spine',
        (elbow + wrist) * .5 - axis * (.15 * scale),
        (.095 * scale, .130 * scale, .28 * scale), darkmetal, .008,
        rot=(wrist - elbow).to_track_quat('Z', 'Y').to_euler())
    for f in (.24, .56, .82):
        q = elbow.lerp(wrist, f) + axis * (.135 * scale)
        o = box(tag + ' forearm guard', q,
                (.140 * scale, .235 * scale, .255 * scale), yellow, .014)
        o.rotation_euler = (wrist - elbow).to_track_quat('Z', 'Y').to_euler()
        bolt(tag + ' forearm guard bolt', q + axis * .058, axis,
             .015, .012, bare)
    arm_joint(tag + ' wrist', wrist, axis, 1.45 * scale)
    # compact faceplate and the actual gripper/tool pointing into the work
    wrist = Vector(wrist); tool_tip = Vector(tool_tip)
    tool_dir = tool_tip - wrist
    cyl(tag + ' wrist black housing', wrist + tool_dir.normalized() * .03,
        .115 * scale, .13, darkmetal, axis=tool_dir, verts=24)
    box(tag + ' wrench gripper body', wrist + tool_dir.normalized() * .12,
        (.16 * scale, .11 * scale, .20 * scale), steel, .012,
        rot=(tool_dir).to_track_quat('Z', 'Y').to_euler())
    rod(tag + ' tool spindle', wrist + tool_dir * .10,
        wrist + tool_dir * .66, .055 * scale, bare)
    cyl(tag + ' tool collar', wrist + tool_dir * .70, .095 * scale, .085,
        darkmetal, axis=tool_dir, verts=20)
    cyl(tag + ' tool red band', wrist + tool_dir * .79, .098 * scale, .022,
        red, axis=tool_dir, verts=20)
    for side in (-1, 1):
        off = axis * (.085 * scale * side)
        beam(tag + ' gripper jaw', wrist + tool_dir * .74 + off,
             wrist + tool_dir * .98 + off * 1.45,
             .048, .068, bare, .006)
    tube(tag + ' black service loom',
         [base + axis * .18, shoulder + axis * .22 + Vector((0, 0, .12)),
          elbow + axis * .21, wrist + axis * .16], .022, rubber)
    box(tag + ' arm cable clamp',
        shoulder + axis * .22 + Vector((0, 0, .02)),
        (.14, .12, .12), darkmetal, .008)
    # small warning decal and red pointer on the shoulder
    box(tag + ' arm warning label',
        shoulder + axis * (.23 * scale) + Vector((0, 0, .12)),
        (.085, .012, .055), label, .002,
        rot=(0, 0, math.radians(base_a + 90)))
    cyl(tag + ' arm red indicator',
        shoulder + Vector((0, 0, .17)) + axis * (.12 * scale),
        .025, .018, glow_red, axis=axis, verts=12)

# left, tall arm: shoulder high, elbow above rim, wrist toward front-left centre
build_arm('Left primary manipulator', 148, .10,
          (-.70, .50, 1.56), (-.30, .04, 1.26), (-.18, -.03, 1.16), 1.14)
# right arm: big horizontal shoulder, reaches diagonally into the well
build_arm('Right primary manipulator', 54, .14,
          (.54, .42, 1.42), (.11, .04, 1.12), (.00, -.02, 1.07), 1.03)
# front auxiliary arm: smaller and darker, tucked into the opening
build_arm('Front auxiliary manipulator', -31, .10,
          (-.34, -.38, 1.24), (-.05, -.17, .96), (.01, -.12, .91), .78)

# extra small arm detail / tool at the left of the work bed
cyl('Auxiliary tool post', (-.43, -.10, .49), .055, .35, darkmetal, verts=20)
cyl('Auxiliary tool pivot', (-.43, -.10, .68), .075, .06, yellow2, axis=(0, 1, 0), verts=18)
beam('Auxiliary tool arm', (-.43, -.10, .68), (-.25, -.06, .58),
     .06, .07, yellow2, .008)
bolt('Auxiliary tool bolt', (-.25, -.06, .58), (0, 0, 1), .024, .02, bare)

# ---------------------------------------------------------------------------
# external service architecture: pipes, pods, radiators, tanks, screens
# ---------------------------------------------------------------------------
# Rear-right blocky motor/generator pods (screen upper right).
for k, (a, r, z, size, mat) in enumerate([
        (47, 1.55, 1.02, (.38, .27, .28), armor_b),
        (70, 1.50, 1.12, (.31, .23, .24), rustmetal),
        (31, 1.55, .86, (.25, .19, .22), armor_c)]):
    p = polar(r, a, z)
    o = box(f'Rear electrical motor pod {k}', p, size, mat, .018,
            rot=(0, 0, math.radians(a + 90)))
    # copper terminal lid
    q = p + Vector((0, 0, size[2] * .53))
    o2 = box(f'Motor pod copper terminal {k}', q, (size[0] * .70, size[1] * .70, .055),
             copper, .008, rot=(0, 0, math.radians(a + 90)))
    for j in range(3):
        bolt(f'Motor pod terminal bolt {k}.{j}', q + Vector((0, 0, .035)) +
             Vector((math.cos(math.radians(a + 90)) * (j - 1) * .09,
                     math.sin(math.radians(a + 90)) * (j - 1) * .09, 0)),
             (0, 0, 1), .018, .016, bare)
    # little vent slats on the front face
    for j in range(4):
        vp = p + Vector((math.cos(math.radians(a + 90)) * .0,
                         math.sin(math.radians(a + 90)) * .0,
                         (j - 1.5) * .047))
        vp += Vector((math.cos(math.radians(a)) * (size[0] * .50),
                      math.sin(math.radians(a)) * (size[0] * .50), 0))
        o3 = box(f'Motor pod vent {k}.{j}', vp, (.012, .12, .020), darkmetal, .002,
                 rot=(0, 0, math.radians(a + 90)))

# Rear-left copper/steel pipe cluster, with several elbows and clamps.
rear_left = [
    (137, 1.45, .67, 1.58, 1.00),
    (151, 1.38, .73, 1.50, 1.22),
    (165, 1.42, .58, 1.57, 1.13),
    (124, 1.48, .54, 1.57, .96),
]
for k, (a, r0, z0, r1, z1) in enumerate(rear_left):
    p0 = polar(r0, a, z0)
    p1 = polar(r1, a - 4, z1)
    pts = [p0, polar((r0 + r1) * .5, a + 7, (z0 + z1) * .5 + .10), p1]
    tube(f'Rear left copper riser {k}', pts, .040 if k % 2 else .030,
         copper if k != 2 else steel, resolution=5)
    # lower elbow collar
    cyl(f'Riser lower collar {k}', p0, .055, .035, brass, verts=16)
    bolt(f'Riser clamp bolt {k}', polar(1.58, a - 4, z1),
         (math.cos(math.radians(a)), math.sin(math.radians(a)), 0), .022, .018, bare)
# one big hooked pipe on the far left, like the reference's bent elbow
# A cluster of hooked pipes over the far-left rim.  The reference has a very
# readable bent elbow silhouette here, so this is deliberately oversized.
big_pipe_sets = [
    ([polar(1.58, 176, .46), polar(1.76, 179, .64),
      polar(1.80, 184, .91), polar(1.69, 187, 1.11),
      polar(1.48, 180, 1.18)], .066, rustmetal),
    ([polar(1.66, 164, .53), polar(1.82, 168, .73),
      polar(1.79, 174, .94), polar(1.61, 177, 1.12)], .040, copper),
    ([polar(1.50, 188, .59), polar(1.66, 194, .79),
      polar(1.65, 195, 1.01), polar(1.50, 190, 1.14)], .030, bluepipe),
]
for k, (pts, rad, mat) in enumerate(big_pipe_sets):
    tube(f'Large hooked left service pipe {k}', pts, rad, mat, resolution=6)
    # flange rings at the base and top
    for j, p in enumerate((pts[0], pts[-1])):
        cyl(f'Hooked pipe flange {k}.{j}', p, rad * 1.55, .035, brass, verts=18)
    if k == 0:
        for j, p in enumerate(pts[1:-1]):
            cyl(f'Hooked pipe joint collar {k}.{j}', p, rad * 1.45, .045,
                darkmetal, verts=18)
# cast bracket tying the pipe cluster back to the rim
for k, a in enumerate((168, 178, 188)):
    p = polar(1.54, a, .92)
    box(f'Hooked pipe bracket {k}', p, (.09, .12, .26), darkmetal, .006,
        rot=(0, 0, math.radians(a)))
    bolt(f'Hooked pipe bracket bolt {k}', polar(1.60, a, .88),
         (math.cos(math.radians(a)), math.sin(math.radians(a)), 0),
         .022, .018, bare)

# Left-front large cylindrical canister and its plumbing.
p = polar(1.72, -156, .29)
cyl('Left front dirty reservoir', p, .19, .55, rustmetal, verts=28)
cyl('Reservoir top cap', p + Vector((0, 0, .305)), .135, .055, steel, verts=20)
cyl('Reservoir bottom band', p + Vector((0, 0, -.255)), .198, .045, darkmetal, verts=28)
tube('Reservoir drain pipe',
     [p + Vector((0, 0, -.20)), polar(1.65, -143, .13), polar(1.77, -124, .25)],
     .033, copper, resolution=5)
# small side tap and warning label
cyl('Reservoir side tap', polar(1.88, -156, .27), .045, .13, brass,
    axis=(math.cos(math.radians(-156)), math.sin(math.radians(-156)), 0), verts=16)
box('Reservoir warning plate', polar(1.88, -153, .43), (.12, .016, .09),
    label, .003, rot=(0, 0, math.radians(-63)))

# Front-right red suppression bottle and green diagnostic panel.
p = polar(1.68, -24, .29)
cyl('Right front red suppression bottle', p, .150, .50, red, verts=24)
cyl('Suppression neck', p + Vector((0, 0, .29)), .055, .12, steel, verts=16)
cyl('Suppression valve', p + Vector((0, 0, .37)), .075, .040, darkmetal, verts=16)
tube('Suppression black feed tube',
     [p + Vector((0, 0, .27)), polar(1.38, -16, .64), polar(1.30, -8, .82)],
     .024, rubber, resolution=5)
# green monitor frame
p = polar(1.77, -48, .54)
mon = box('Angled green diagnostic monitor', p, (.38, .17, .30), darkmetal, .014,
          rot=(0, 0, math.radians(42)))
scr = box('Green diagnostic screen', polar(1.84, -48, .555), (.27, .022, .17),
          glow_green, .004, rot=(0, 0, math.radians(42)))
# little lighter frame around the screen
box('Green screen lower frame', polar(1.85, -48, .455), (.29, .022, .030),
    armor_c, .003, rot=(0, 0, math.radians(42)))

# right-side radiator / vent tower
p = polar(1.66, 14, .56)
rad = box('Right side electrical radiator', p, (.17, .36, .42), armor_b, .012,
          rot=(0, 0, math.radians(14)))
for j in range(7):
    q = p + Vector((0, 0, -.155 + j * .052))
    o = box(f'Radiator cooling slat {j}', q + polar(.09, 14, 0), (.035, .30, .022),
            bare if j % 3 else darkmetal, .003, rot=(0, 0, math.radians(14)))
cyl('Radiator fan housing', polar(1.75, 14, .78), .10, .08, darkmetal,
    axis=(math.cos(math.radians(14)), math.sin(math.radians(14)), 0), verts=24)
cyl('Radiator fan hub', polar(1.80, 14, .78), .032, .025, steel,
    axis=(math.cos(math.radians(14)), math.sin(math.radians(14)), 0), verts=12)

# front service junction boxes / labels on the lower skirt
for k, a in enumerate([-174, -132, -111, -69, -7, 22, 90, 121, 160]):
    p = polar(1.665, a, .34 if k % 2 else .48)
    box(f'Lower service junction box {k}', p, (.16, .035, .14),
        armor_c if k % 3 else rustmetal, .006,
        rot=(0, 0, math.radians(a + 90)))
    box(f'Junction label {k}', p + polar(.02, a, 0), (.10, .012, .045),
        label, .002, rot=(0, 0, math.radians(a + 90)))
    bolt(f'Junction box bolt {k}', p + polar(.07, a + 7, 0), (0, 0, 1),
         .012, .012, bare)

# front-left bank of exposed copper/black hoses
for k in range(5):
    a = -121 + k * 5
    pts = [polar(1.60, a, .18), polar(1.66, a + 6, .36),
           polar(1.58, a + 9, .58), polar(1.40, a + 7, .72)]
    tube(f'Front left exposed hose {k}', pts, .012 if k % 2 else .018,
         rubber if k % 3 else copper, resolution=4)
# red/black/turquoise small wires behind the front-right screen
for k in range(6):
    a = -42 + k * 3.5
    tube(f'Right front control wire {k}',
         [polar(1.36, a, .31), polar(1.52, a + 4, .42),
          polar(1.55, a + 3, .59), polar(1.44, a + 8, .72)],
         .008, red if k % 3 == 0 else rubber, resolution=4)

# Dense front and right-side equipment bank.  Small boxes, sockets, labels and
# exposed cable runs are what give the reference its "used industrial machine"
# density at game-camera distance.
for k, a in enumerate([-158, -138, -118, -98, -78, -58, -38, -18, 2, 22]):
    z = .56 if k % 3 else .66
    p = polar(1.690, a, z)
    mat = [armor_c, rustmetal, armor_b, darkmetal][k % 4]
    box(f'Front service junction box {k}', p, (.19, .060, .16), mat, .008,
        rot=(0, 0, math.radians(a + 90)))
    q = p + Vector((math.cos(math.radians(a)) * .035,
                    math.sin(math.radians(a)) * .035, 0))
    box(f'Front service faceplate {k}', q, (.145, .015, .105), armor_b, .003,
        rot=(0, 0, math.radians(a + 90)))
    box(f'Front service pale label {k}', q + Vector((0, 0, -.015)),
        (.095, .010, .037), label, .0015,
        rot=(0, 0, math.radians(a + 90)))
    ledp = p + Vector((math.cos(math.radians(a)) * .068,
                       math.sin(math.radians(a)) * .068, .052))
    cyl(f'Front service indicator {k}', ledp, .020, .022,
        glow_red if k % 6 == 0 else steel,
        axis=(math.cos(math.radians(a)), math.sin(math.radians(a)), 0), verts=10)
    bolt(f'Front service bolt {k}.0', p + polar(.065, a + 90, .06),
         (math.cos(math.radians(a)), math.sin(math.radians(a)), 0), .013, .011, bare)
    bolt(f'Front service bolt {k}.1', p + polar(.065, a - 90, .06),
         (math.cos(math.radians(a)), math.sin(math.radians(a)), 0), .013, .011, bare)

# Coolant line running around the right-hand shoulder with elbows and clamps.
for a0, a1, z, rad, mat in [(-36, 74, .755, .027, bluepipe),
                            (-68, 48, .315, .021, copper),
                            (12, 104, .63, .018, rubber)]:
    pts = []
    for i in range(25):
        a = a0 + (a1 - a0) * i / 24
        zz = z + .024 * math.sin(i * .9)
        pts.append(polar(1.63 + .025 * math.sin(i * 1.7), a, zz))
    tube('Exterior wrapped service line', pts, rad, mat, resolution=3)
    for i in range(4):
        a = a0 + (a1 - a0) * i / 3
        p = polar(1.66, a, z)
        box('Exterior line clamp', p, (.05, .085, .06), darkmetal, .004,
            rot=(0, 0, math.radians(a + 90)))

# Heavy black/copper cable bundles draped down the left and right front.
for k, a in enumerate([-172, -150, -128, -52, -32, -12, 8, 28]):
    pts = [polar(1.42, a, .84), polar(1.58, a + 2, .68),
           polar(1.68, a + 7, .48), polar(1.64, a + 12, .26),
           polar(1.70, a + 18, .19)]
    tube(f'Exterior hanging cable {k}', pts,
         .013 if k % 2 else .020, rubber if k % 3 else copper, resolution=5)
    if k % 2:
        tube(f'Exterior thin signal wire {k}',
             [polar(1.48, a + 3, .74), polar(1.58, a + 8, .54),
              polar(1.61, a + 13, .34)], .006, red, resolution=4)

# Row of little dirty identification plates along the lower front rim.
for k in range(13):
    a = -168 + k * 14
    p = polar(1.66, a, .205)
    box(f'Lower inventory placard {k}', p, (.105, .012, .052),
        label, .002, rot=(0, 0, math.radians(a + 90)))
    if k % 4 == 0:
        cyl(f'Placard fastener {k}', p + polar(.05, a + 90, 0), .008, .010,
            bare, axis=(math.cos(math.radians(a)), math.sin(math.radians(a)), 0), verts=8)

# Small exposed motor/gearbox on the left shoulder and the right rear.
for k, (a, z, size) in enumerate([(-111, .79, (.30, .20, .24)),
                                  (-143, .68, (.23, .16, .20)),
                                  (99, .71, (.28, .18, .22)),
                                  (126, .86, (.20, .14, .18))]):
    p = polar(1.57, a, z)
    box(f'Shoulder auxiliary motor {k}', p, size, rustmetal if k % 2 else armor_b,
        .012, rot=(0, 0, math.radians(a + 90)))
    cyl(f'Auxiliary motor bearing {k}', p, .085, .055, darkmetal,
        axis=(math.cos(math.radians(a)), math.sin(math.radians(a)), 0), verts=20)
    for j in range(3):
        box(f'Auxiliary motor vent {k}.{j}',
            p + Vector((0, 0, -.05 + j * .045)) + polar(size[0] * .5, a, 0),
            (.015, .12, .020), darkmetal, .002,
            rot=(0, 0, math.radians(a + 90)))

# A little mounting cage and ceramic insulators on the rear-left corner.
p = polar(1.58, 162, .87)
box('Rear left electrical cage', p, (.22, .17, .25), darkmetal, .010,
    rot=(0, 0, math.radians(162 + 90)))
for j, aa in enumerate((156, 168)):
    cyl(f'Ceramic insulator {j}', polar(1.52, aa, 1.00), .038, .15,
        white_metal, verts=14)
    cyl(f'Insulator cap {j}', polar(1.52, aa, 1.085), .050, .025, brass, verts=14)

# Oversized bolt-on modules at the upper right and upper left.  These break
# the circular silhouette and become the large readable shapes in the
# reference's top-right corner.
for k, (a, r, z, size, mat) in enumerate([
        (58, 1.78, .83, (.54, .44, .40), armor_b),
        (83, 1.76, .94, (.44, .36, .34), rustmetal),
        (116, 1.75, .88, (.32, .28, .29), armor_c),
        (139, 1.74, .84, (.27, .24, .26), armor_b)]):
    p = polar(r, a, z)
    box(f'Oversized bolt-on module {k}', p, size, mat, .018,
        rot=(0, 0, math.radians(a + 90)))
    cap = p + Vector((0, 0, size[2] * .51))
    box(f'Oversized module dark top frame {k}', cap,
        (size[0] * .90, size[1] * .90, .035), darkmetal, .008,
        rot=(0, 0, math.radians(a + 90)))
    # The four upper modules are the four quality-colour indicators:
    # uncommon green, rare blue, epic purple and legendary orange.
    box(f'Oversized module top service plate {k}', cap + Vector((0, 0, .027)),
        (size[0] * .62, size[1] * .60, .020), armor_c, .006,
        rot=(0, 0, math.radians(a + 90)))
    box(f'Oversized module bottom collar {k}',
        p - Vector((0, 0, size[2] * .49)),
        (size[0] * .94, size[1] * .94, .055), darkmetal, .008,
        rot=(0, 0, math.radians(a + 90)))
    # vertical ribs on the outward face
    face = p + Vector((math.cos(math.radians(a)) * (size[1] * .50),
                       math.sin(math.radians(a)) * (size[1] * .50), 0))
    for j in range(4):
        box(f'Oversized module vent {k}.{j}', face + Vector((0, 0, (j - 1.5) * .070)),
            (.015, size[0] * .62, .030), darkmetal, .003,
            rot=(0, 0, math.radians(a + 90)))
    box(f'Oversized module face plate {k}', face + polar(.010, a, .02),
        (size[0] * .44, .018, size[2] * .48), armor_b, .004,
        rot=(0, 0, math.radians(a + 90)))
    # Small recessed quality identification windows: neutral equipment with
    # a restrained colour code instead of a full coloured plastic face.
    box(f'Oversized module quality bezel top {k}', cap + Vector((0, 0, .040)),
        (size[0] * .40, size[1] * .24, .012), darkmetal, .002,
        rot=(0, 0, math.radians(a + 90)))
    box(f'Oversized module quality window top {k}', cap + Vector((0, 0, .048)),
        (size[0] * .31, size[1] * .16, .008), quality_mats[k], .001,
        rot=(0, 0, math.radians(a + 90)))
    box(f'Oversized module quality bezel face {k}', face + polar(.009, a, .02),
        (size[0] * .24, .015, size[2] * .15), darkmetal, .002,
        rot=(0, 0, math.radians(a + 90)))
    box(f'Oversized module quality window face {k}', face + polar(.018, a, .02),
        (size[0] * .18, .010, size[2] * .11), quality_mats[k], .001,
        rot=(0, 0, math.radians(a + 90)))
    for j, aaa in enumerate((a - 8, a + 8)):
        bolt(f'Oversized module bolt {k}.{j}', cap + polar(size[0] * .34, aaa, 0),
             (0, 0, 1), .028, .024, bare)
    # a copper conduit entering the side of each module
    tube(f'Oversized module conduit {k}',
         [polar(1.66, a + 12, .62), polar(1.78, a + 8, .84),
          p + Vector((math.cos(math.radians(a + 90)) * size[0] * .30,
                      math.sin(math.radians(a + 90)) * size[0] * .30,
                      -size[2] * .25))],
         .020, copper, resolution=4)
    # a heavy short cable leaving the bottom of the module
    tube(f'Oversized module cable {k}',
         [p - Vector((0, 0, size[2] * .45)),
          polar(1.70, a + 8, .70), polar(1.55, a + 13, .50)],
         .020, rubber, resolution=4)

# Left front external reservoir: large enough to read as a separate tank at
# the lower-left edge, with bands, a valve and a bent copper feed.
p = polar(1.82, -153, .27)
cyl('Large left external reservoir', p, .225, .58, rustmetal, verts=32)
cyl('Large reservoir upper cap', p + Vector((0, 0, .305)), .155, .060, steel, verts=24)
cyl('Large reservoir lower foot', p + Vector((0, 0, -.305)), .19, .045, darkmetal, verts=24)
for zz in (-.22, -.10, .02, .14, .24):
    ring = cyl('Large reservoir band', p + Vector((0, 0, zz)), .233, .022,
               darkmetal, verts=32)
tube('Large reservoir copper elbow',
     [p + Vector((0, 0, .32)), polar(1.79, -143, .58),
      polar(1.62, -135, .76), polar(1.48, -129, .88)],
     .040, copper, resolution=5)
cyl('Large reservoir valve', polar(1.84, -166, .21), .055, .16,
    brass, axis=(math.cos(math.radians(-166)), math.sin(math.radians(-166)), 0), verts=18)
box('Large reservoir label', polar(1.99, -150, .36), (.12, .014, .085),
    label, .003, rot=(0, 0, math.radians(-60)))

# Thick bent utility pipes draped over the visible front shell.
for k, (a0, a1, z0, z1, rad, mat) in enumerate([
        (-158, -105, .80, .38, .040, copper),
        (-120, -62, .77, .26, .032, darkmetal),
        (-72, -15, .81, .33, .045, bluepipe),
        (12, 70, .83, .34, .036, copper),
        (84, 132, .78, .41, .030, bluepipe)]):
    pts = []
    for i in range(9):
        f = i / 8
        aa = a0 + (a1 - a0) * f
        zz = z0 + (z1 - z0) * f + .035 * math.sin(f * math.pi * 2 + k)
        pts.append(polar(1.72 + .025 * math.sin(i * 1.3), aa, zz))
    tube(f'Thick exterior bent utility pipe {k}', pts, rad, mat, resolution=5)
    for i in range(3):
        aa = a0 + (a1 - a0) * i / 2
        zz = z0 + (z1 - z0) * i / 2
        p = polar(1.73, aa, zz)
        box(f'Thick utility pipe clamp {k}.{i}', p, (.045, .09, .075),
            darkmetal, .004, rot=(0, 0, math.radians(aa + 90)))
        bolt(f'Thick utility pipe clamp bolt {k}.{i}',
             polar(1.78, aa, zz),
             (math.cos(math.radians(aa)), math.sin(math.radians(aa)), 0),
             .014, .012, bare)

# Vent banks and warning placards on the lower front shell.
for bank, a in enumerate([-154, -116, -76, -36, 4, 42]):
    for j in range(5):
        aa = a + (j - 2) * 2.8
        p = polar(1.705, aa, .235 + (j % 2) * .015)
        box(f'Lower vent slat {bank}.{j}', p, (.055, .018, .115),
            darkmetal, .003, rot=(0, 0, math.radians(aa + 90)))
    p = polar(1.712, a, .15)
    box(f'Lower vent backing {bank}', p, (.18, .020, .155), armor_b, .004,
        rot=(0, 0, math.radians(a + 90)))

for k in range(7):
    a = -147 + k * 23
    p = polar(1.716, a, .56)
    box(f'Front warning label {k}', p, (.10, .012, .045), label, .002,
        rot=(0, 0, math.radians(a + 90)))
    if k % 2 == 0:
        box(f'Red warning stripe {k}', p + polar(.065, a + 90, 0),
            (.025, .010, .040), red, .001,
            rot=(0, 0, math.radians(a + 90)))

# A handrail / maintenance cage along the rear half of the upper rim.
for i in range(11):
    a = 40 + i * 25
    p = polar(1.43, a, 1.15)
    rod(f'Rear rim handrail post {i}', polar(1.43, a, 1.05),
        polar(1.43, a, 1.22), .012, darkmetal)
    cyl(f'Rear rim handrail foot {i}', polar(1.43, a, 1.05), .026,
        .026, steel, verts=10)
rail_pts = [polar(1.43, 40 + i * 25, 1.22) for i in range(11)]
tube('Rear rim upper handrail', rail_pts, .014, steel, resolution=4)
for i in range(3):
    aa = 62 + i * 55
    tube(f'Rear rim safety chain {i}',
         [polar(1.43, aa, 1.21), polar(1.43, aa + 18, 1.12),
          polar(1.43, aa + 35, 1.21)], .007, copper, resolution=4)

# Prominent forward-facing segmented diagnostic panel.  The cells and dark
# dividers are deliberately large so the LCD segmentation survives Factorio's
# 0.5 sprite scale instead of turning into one coloured blob.
a_screen = -38
p_screen = polar(1.735, a_screen, .535)
box('Green screen dark frame', p_screen, (.42, .055, .30), darkmetal, .010,
    rot=(0, 0, math.radians(a_screen + 90)))
for j, zz in enumerate((-.085, 0.0, .085)):
    box(f'Green screen bright cell {j}', p_screen + polar(.044, a_screen, zz),
        (.34, .018, .060), glow_green, .005,
        rot=(0, 0, math.radians(a_screen + 90)))
for j, zz in enumerate((-.0425, .0425)):
    box(f'Green screen separator row {j}', p_screen + polar(.058, a_screen, zz),
        (.355, .020, .020), darkmetal, .001,
        rot=(0, 0, math.radians(a_screen + 90)))
box('Green screen separator column', p_screen + polar(.059, a_screen, 0),
    (.018, .020, .235), darkmetal, .001,
    rot=(0, 0, math.radians(a_screen + 90)))
for j, off in enumerate((-.105, .105)):
    tang = Vector((-math.sin(math.radians(a_screen)),
                   math.cos(math.radians(a_screen)), 0.0))
    box(f'Green screen grille rib {j}', p_screen + polar(.059, a_screen, 0) + tang * off,
        (.014, .020, .235), darkmetal, .001,
        rot=(0, 0, math.radians(a_screen + 90)))
box('Green screen lower bezel', p_screen + Vector((0, 0, -.14)),
    (.35, .022, .030), armor_c, .003,
    rot=(0, 0, math.radians(a_screen + 90)))
for j, aa in enumerate((a_screen - 6, a_screen + 6)):
    bolt(f'Green screen frame bolt {j}',
         p_screen + polar(.15, aa + 90, .10),
         (math.cos(math.radians(a_screen)), math.sin(math.radians(a_screen)), 0),
         .016, .014, bare)
# little cable bundle entering the screen from below
tube('Green screen cable bundle',
     [polar(1.65, a_screen + 5, .34), polar(1.75, a_screen + 3, .45),
      p_screen + Vector((0, 0, -.13))], .014, rubber, resolution=4)

# upper service rail and small indicator lights
for i in range(4):
    a = -120 + i * 55
    p = polar(1.55, a, .81)
    cyl(f'Upper rim indicator {i}', p, .030, .035, glow_red if i % 2 == 0 else steel,
        axis=(math.cos(math.radians(a)), math.sin(math.radians(a)), 0), verts=10)

# ---------------------------------------------------------------------------
# mechanical greebles: gears, vents, bolts and worn metal decals
# ---------------------------------------------------------------------------
def gear(name, center, radius, depth, teeth, mat, axis=(0, 0, 1)):
    c = Vector(center)
    axis = Vector(axis).normalized()
    cyl(name + ' web', c, radius * .72, depth, mat, axis=axis, verts=24)
    for i in range(teeth):
        a = i * 360 / teeth
        q = c + Vector((math.cos(math.radians(a)) * radius,
                        math.sin(math.radians(a)) * radius, 0))
        o = box(name + f' tooth {i:02d}', q, (.055, .040, depth * .88),
                mat, .003)
        o.rotation_euler.z = math.radians(a + 90)
    bolt(name + ' axle', c, axis, radius * .20, depth * 1.3, bare)

gear('Front-left exposed reduction gear', polar(1.67, -137, .56),
     .23, .095, 18, rustmetal, axis=(0, 1, 0))
gear('Right rear small exposed gear', polar(1.62, 59, .76),
     .15, .075, 12, darkmetal, axis=(0, 1, 0))
gear('Lower rear idler gear', polar(1.62, 108, .63),
     .13, .070, 10, steel, axis=(0, 1, 0))

# rivet rings around plate seams and exposed castings
for i in range(30):
    a = i * 12 + 6
    bolt(f'Skirt rivet {i:02d}', polar(1.625, a, .225), (math.cos(math.radians(a)),
         math.sin(math.radians(a)), 0), .016, .014, bare)
for i in range(16):
    a = i * 22.5 + 9
    bolt(f'Collar rivet {i:02d}', polar(1.435, a, .875), (0, 0, 1), .018, .014, bare)

# small pale service labels / scratched inventory plates scattered on the body
label_positions = [(-166, .62, 18), (-105, .53, 8), (-73, .70, -14),
                   (-19, .66, -28), (67, .44, 46), (115, .58, 78)]
for i, (a, z, rot) in enumerate(label_positions):
    p = polar(1.625, a, z)
    o = box(f'Worn inventory label {i}', p, (.13, .018, .075), label, .003,
            rot=(math.radians(90), 0, math.radians(a + rot)))

# chipped paint patches: very thin brown plates, placed on outer plates
for i in range(28):
    a = random.uniform(-170, 170)
    z = random.uniform(.25, .75)
    p = polar(1.626, a, z)
    o = box(f'Chipped paint patch {i}', p, (random.uniform(.035, .10),
             .008, random.uniform(.025, .065)), rustmetal, .002,
            rot=(math.radians(90), 0, math.radians(a)))
# little bright scratches along rims
for i in range(35):
    a = random.uniform(0, 360)
    r = random.choice([1.25, 1.35, 1.46, 1.57])
    p = polar(r, a, random.uniform(.94, 1.05))
    o = box(f'Rim wear scratch {i}', p, (random.uniform(.04, .13), .009, .006),
            bare, .001, rot=(0, 0, math.radians(a + 90)))

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# overlapping repair skins, rust blooms and loose rim cabling
# ---------------------------------------------------------------------------
# These are deliberately geometric rather than only shader noise.  They stay
# readable at the same size as the reference and break the otherwise even
# circular rim into an uneven, repaired assembly.
for i in range(26):
    a = random.uniform(-178, 178)
    w = random.uniform(7, 24)
    z = random.uniform(.24, .74)
    h = random.uniform(.035, .13)
    mat = random.choice([rustmetal, armor_b, darkmetal, armor_c])
    arc_slab(f'Overlapping body repair skin {i:02d}', 1.615, 1.652,
             z, z + h, a, a + w, mat, steps=4, bevel=.004)
    if i % 3 == 0:
        bolt(f'Repair skin rivet {i:02d}', polar(1.665, a + w * .5, z + h * .5),
             Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0)),
             .016, .014, bare if i % 2 else darkmetal)

for i in range(30):
    a = random.uniform(-180, 180)
    z = random.uniform(.23, .77)
    length = random.uniform(.05, .18)
    o = box(f'Rust bloom decal {i:02d}', polar(1.662, a, z),
            (length, .010, random.uniform(.020, .075)), rustmetal, .002,
            rot=(0, 0, math.radians(a + 90)))
    if i % 2:
        o.rotation_euler.x = random.uniform(-.18, .18)

for i in range(22):
    a = random.uniform(0, 360)
    r = random.uniform(1.24, 1.48)
    z = 1.067 + random.uniform(0, .012)
    o = box(f'Worn rim deck patch {i:02d}', polar(r, a, z),
            (random.uniform(.08, .24), random.uniform(.04, .12), .008),
            random.choice([rustmetal, darkmetal, armor_b, steel]), .002,
            rot=(0, 0, math.radians(a + random.uniform(-40, 40))))
    if i % 4 == 0:
        bolt(f'Rim patch rivet {i:02d}', polar(r + .06, a, z + .008),
             (0, 0, 1), .015, .012, bare)

# Several irregular top repair plates with lifted corners.
for i in range(7):
    a0 = random.uniform(-170, 150)
    span = random.uniform(10, 24)
    rr = random.uniform(1.24, 1.38)
    z = 1.045 + random.uniform(0, .025)
    arc_slab(f'Lifted rim repair plate {i:02d}', rr, rr + random.uniform(.08, .15),
             z, z + .026, a0, a0 + span,
             random.choice([armor_c, steel, rustmetal]), steps=5, bevel=.005)

# Loose cables crossing part of the top ring.
for k in range(6):
    a0 = random.uniform(-150, 120)
    a1 = a0 + random.uniform(25, 70)
    r = random.uniform(1.30, 1.48)
    pts = []
    for j in range(7):
        aa = a0 + (a1 - a0) * j / 6
        pts.append(polar(r + random.uniform(-.015, .015), aa,
                         1.072 + .015 * math.sin(j * 1.2 + k)))
    tube(f'Loose rim cable {k}', pts, .012 if k % 2 else .018,
         rubber if k % 3 else copper, resolution=4)

# Thin dark oil drips running down from selected fasteners.
for i in range(18):
    a = random.uniform(-175, 175)
    z = random.uniform(.20, .48)
    h = random.uniform(.08, .20)
    box(f'Vertical oil stain {i:02d}', polar(1.664, a, z - h * .5),
        (random.uniform(.012, .032), .008, h), darkmetal, .001,
        rot=(0, 0, math.radians(a + 90)))

# Give the machine the taller, heavier stance of the reference.  Factorio's
# machine is visibly deeper than a shallow bowl; a controlled Z stretch keeps
# the footprint and all greeble positions while making the sidewall read.
Z_STRETCH = 1.22
for o in list(bpy.context.scene.objects):
    if o.type in {'MESH', 'CURVE'}:
        o.location.z *= Z_STRETCH
        o.scale.z *= Z_STRETCH

# lights, floor and camera
# ---------------------------------------------------------------------------
# white studio floor; a shadow catcher is used for a clean white presentation
# field while preserving contact darkness.
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.012))
floor = bpy.context.object
floor.name = 'White presentation floor'
fm = bpy.data.materials.new('Floor | warm white')
fm.use_nodes = True
fb = fm.node_tree.nodes.get('Principled BSDF')
fb.inputs['Base Color'].default_value = (.80, .78, .72, 1)
fb.inputs['Roughness'].default_value = .92
floor.data.materials.append(fm)
floor.pass_index = 1

# world: neutral pale studio environment
world = bpy.data.worlds.new('White studio world')
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value = (.78, .78, .78, 1)
bg.inputs['Strength'].default_value = .17
bpy.context.scene.world = world

def area_light(name, loc, energy, size, color, target=(0, 0, .55)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    o = bpy.context.object
    o.name = name
    o.data.energy = energy
    o.data.shape = 'DISK'
    o.data.size = size
    o.data.color = color
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()
    return o

# Back-left warm key makes a long eastward ground shadow, matching the
# reference's upper-left sun.
area_light('Neutral back-left key', (-5.8, 4.2, 9.0), 220, 2.8, (1.0, .86, .72))
area_light('Cool front-right fill', (5.0, -4.8, 5.2), 140, 5.2, (.58, .72, 1.0))
area_light('Soft overhead rim', (1.0, 1.0, 10.0), 85, 3.6, (1.0, .92, .78))
area_light('Lower-left front fill', (-4.8, -5.6, 2.9), 150, 4.6, (.72, .82, 1.0))
bpy.ops.object.light_add(type='SUN', location=(-6.0, 4.0, 9.0))
sun = bpy.context.object
sun.name = 'Crisp upper-left sun'
sun.data.energy = 4.9
sun.data.angle = math.radians(2.2)
sun.data.color = (1.0, .91, .80)
sun.rotation_euler = (Vector((0, 0, .45)) - sun.location).to_track_quat('-Z', 'Y').to_euler()

# warm practical inside the processing well
bpy.ops.object.light_add(type='POINT', location=(0, .12, 1.02))
inside = bpy.context.object
inside.name = 'Warm chamber practical'
inside.data.energy = 75
inside.data.color = (1.0, .30, .045)
inside.data.shadow_soft_size = .32
bpy.ops.object.light_add(type='POINT', location=(0, -.16, .91))
tablelight = bpy.context.object
tablelight.name = 'Work-bed warm task light'
tablelight.data.energy = 85
tablelight.data.color = (1.0, .52, .20)
tablelight.data.shadow_soft_size = .14
bpy.ops.object.light_add(type='POINT', location=(-.24, .18, 1.02))
rimlight = bpy.context.object
rimlight.name = 'Chamber cool rim practical'
rimlight.data.energy = 32
rimlight.data.color = (.55, .72, 1.0)
rimlight.data.shadow_soft_size = .16

# orthographic inspection camera, aimed from front-right and elevated so the
# open chamber, front armour and right-side services all read at once.
cam_target = Vector((0, 0, .82))
cam_loc = Vector((3.2, -8.4, 9.0))
bpy.ops.object.camera_add(location=cam_loc)
cam = bpy.context.object
cam.name = 'Reference-match orthographic camera'
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 10.7
cam.rotation_euler = (cam_target - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene = bpy.context.scene
scene.camera = cam
def use_gpu(scene):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.refresh_devices()
    for dev in prefs.devices:
        dev.use = (dev.type == 'OPTIX')
    scene.cycles.device = 'GPU'

use_gpu(scene)

# subtle camera-facing composition: object slightly centred, with the long
# side shadow occupying the empty right-hand field.
scene.render.engine = 'CYCLES'
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces = 3
scene.cycles.glossy_bounces = 3
scene.cycles.transmission_bounces = 2
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = .035
scene.render.resolution_x = 2000
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(OUT / 'quality-upcycler-reference-match-raw.png')
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = -0.02

# Compositor: replace the studio floor with a clean white field while
# preserving the rendered contact/cast shadow.  An object-index mask keeps the
# correction from touching the machine.
scene.use_nodes = True
scene.view_layers[0].use_pass_object_index = True
bpy.context.view_layer.use_pass_object_index = True
comp = scene.node_tree
comp.nodes.clear()
rl = comp.nodes.new('CompositorNodeRLayers')
idmask = comp.nodes.new('CompositorNodeIDMask')
idmask.index = 1
idmask.use_antialiasing = True
comp.links.new(rl.outputs['IndexOB'], idmask.inputs['ID value'])
bw = comp.nodes.new('CompositorNodeRGBToBW')
comp.links.new(rl.outputs['Image'], bw.inputs['Image'])
mr = comp.nodes.new('CompositorNodeMapRange')
mr.inputs['From Min'].default_value = 0.10
mr.inputs['From Max'].default_value = 0.46
mr.inputs['To Min'].default_value = 0.15
mr.inputs['To Max'].default_value = 1.0
try:
    mr.clamp = True
except Exception:
    pass
comp.links.new(bw.outputs['Val'], mr.inputs['Value'])
v2c = comp.nodes.new('CompositorNodeValToRGB')
cr = v2c.color_ramp
cr.interpolation = 'LINEAR'
cr.elements[0].position = 0.0
cr.elements[0].color = (0, 0, 0, 1)
cr.elements[1].position = 1.0
cr.elements[1].color = (1, 1, 1, 1)
comp.links.new(mr.outputs['Value'], v2c.inputs['Fac'])
floor_mix = comp.nodes.new('CompositorNodeMixRGB')
floor_mix.blend_type = 'MIX'
comp.links.new(idmask.outputs['Alpha'], floor_mix.inputs[0])
comp.links.new(rl.outputs['Image'], floor_mix.inputs[1])
comp.links.new(v2c.outputs['Image'], floor_mix.inputs[2])
gl = comp.nodes.new('CompositorNodeGlare')
gl.glare_type = 'FOG_GLOW'
gl.quality = 'HIGH'
gl.threshold = 1.2
gl.size = 7
gl.mix = -0.90
comp.links.new(floor_mix.outputs[0], gl.inputs['Image'])
mix = comp.nodes.new('CompositorNodeMixRGB')
mix.blend_type = 'ADD'
mix.inputs[0].default_value = 0.10
comp.links.new(floor_mix.outputs[0], mix.inputs[1])
comp.links.new(gl.outputs['Image'], mix.inputs[2])
comp.links.new(floor_mix.outputs[0], comp.nodes.new('CompositorNodeComposite').inputs['Image'])

# Save the editable model before rendering.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'quality-upcycler-reference-match.blend'))
bpy.ops.render.render(write_still=True)

# also render a transparent, tightly framed source for later compositing / icon
floor.hide_render = True
scene.use_nodes = False
scene.render.film_transparent = True
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.filepath = str(OUT / 'quality-upcycler-reference-match-square.png')
cam.data.ortho_scale = 4.9
cam.location = Vector((3.0, -7.2, 9.4))
cam.rotation_euler = (Vector((0, 0, .93)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.render.render(write_still=True)













































