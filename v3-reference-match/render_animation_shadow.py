"""Ground-projected shadow for the animation atlas; same camera scale/origin."""
import bpy
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE / 'quality-upcycler-reference-match-animated.blend'))
scene = bpy.context.scene
def use_gpu(scene):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.refresh_devices()
    for dev in prefs.devices:
        dev.use = (dev.type == 'OPTIX')
    scene.cycles.device = 'GPU'

use_gpu(scene)
scene.use_nodes = False
scene.render.film_transparent = True
scene.render.resolution_x = 480
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.frame_set(101)
bpy.context.view_layer.update()

# Match the 320 px frame's world scale: 480 / 320 * 4.95.
cam = bpy.data.objects['Reference-match orthographic camera']
cam.data.ortho_scale = 7.425
cam.location = Vector((3.05, -7.35, 9.35))
cam.rotation_euler = (Vector((0, 0, .92)) - cam.location).to_track_quat('-Z', 'Y').to_euler()

floor = bpy.data.objects.get('White presentation floor')
if floor:
    floor.hide_render = True
dg = bpy.context.evaluated_depsgraph_get()
verts, faces, casters = [], [], []
for o in list(scene.objects):
    if o.type not in {'MESH', 'CURVE'} or o == floor or 'FLOW' in o.name.upper():
        continue
    casters.append(o)
    e = o.evaluated_get(dg)
    mesh = e.to_mesh()
    offset = len(verts)
    for v in mesh.vertices:
        p = e.matrix_world @ v.co
        # approximately the same light direction used by the Cycles key
        verts.append((p.x + p.z * 1.15, p.y + p.z * .40, .002))
    faces.extend(tuple(offset + i for i in poly.vertices) for poly in mesh.polygons)
    e.to_mesh_clear()
for o in casters:
    o.hide_render = True
if floor:
    floor.hide_render = True

mesh = bpy.data.meshes.new('Projected directional ground shadow')
mesh.from_pydata(verts, [], faces)
mesh.update()
ob = bpy.data.objects.new('Projected directional ground shadow', mesh)
scene.collection.objects.link(ob)
mat = bpy.data.materials.new('Black unlit silhouette')
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()
em = nodes.new('ShaderNodeEmission')
em.inputs[0].default_value = (0, 0, 0, 1)
out = nodes.new('ShaderNodeOutputMaterial')
mat.node_tree.links.new(em.outputs[0], out.inputs[0])
ob.data.materials.append(mat)

scene.render.filepath = str(HERE / 'quality-upcycler-shadow-raw.png')
bpy.ops.render.render(write_still=True)
print('wrote', scene.render.filepath)



