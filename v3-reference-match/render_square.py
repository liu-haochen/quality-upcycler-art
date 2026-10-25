import bpy
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'quality-upcycler-reference-match.blend'))
sc=bpy.context.scene
bpy.data.objects['White presentation floor'].hide_render=True
sc.use_nodes=False
sc.render.film_transparent=True
sc.render.resolution_x=1000; sc.render.resolution_y=1000
sc.render.resolution_percentage=100
sc.cycles.samples=96
sc.render.image_settings.file_format='PNG'
sc.render.image_settings.color_mode='RGBA'
sc.render.filepath=str(HERE/'quality-upcycler-reference-match-square.png')
cam=bpy.data.objects['Reference-match orthographic camera']
cam.data.ortho_scale=4.9
cam.location=Vector((3.0,-7.2,9.4))
cam.rotation_euler=(Vector((0,0,.93))-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.render.render(write_still=True)
