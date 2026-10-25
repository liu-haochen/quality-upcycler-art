"""Regenerate the wide static presentation from the final animated rig."""
import bpy
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'quality-upcycler-reference-match-animated.blend'))
sc=bpy.context.scene
def use_gpu(scene):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.refresh_devices()
    for dev in prefs.devices:
        dev.use = (dev.type == 'OPTIX')
    scene.cycles.device = 'GPU'
use_gpu(sc)
sc.frame_set(113)
floor=bpy.data.objects.get('White presentation floor')
if floor: floor.hide_render=False
sc.use_nodes=True
sc.render.film_transparent=False
sc.render.resolution_x=2000; sc.render.resolution_y=700; sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGB'
sc.cycles.samples=96; sc.cycles.use_denoising=True
cam=bpy.data.objects['Reference-match orthographic camera']
cam.data.ortho_scale=10.7
cam.location=Vector((3.2,-8.4,9.0))
cam.rotation_euler=(Vector((0,0,.82))-cam.location).to_track_quat('-Z','Y').to_euler()
sc.render.filepath=str(HERE/'quality-upcycler-reference-match-raw.png')
bpy.ops.render.render(write_still=True)
# transparent square preview at the same working pose
floor.hide_render=True
sc.use_nodes=False
sc.render.film_transparent=True
sc.render.resolution_x=1000; sc.render.resolution_y=1000
sc.render.image_settings.color_mode='RGBA'
cam.data.ortho_scale=4.95
cam.location=Vector((3.05,-7.35,9.35))
cam.rotation_euler=(Vector((0,0,.92))-cam.location).to_track_quat('-Z','Y').to_euler()
sc.render.filepath=str(HERE/'quality-upcycler-reference-match-square.png')
bpy.ops.render.render(write_still=True)
print('static previews updated')

