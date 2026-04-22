import bpy
import sys
import math

argv = sys.argv
argv = argv[argv.index("--") + 1:]

output = argv[0]
prompt = argv[1] if len(argv) > 1 else "modern luxury tower"

bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 64
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 180
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.filepath = output

bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 12))
building = bpy.context.object
building.scale = (6, 6, 12)

concrete = bpy.data.materials.new(name="Concrete")
concrete.use_nodes = True
pbsdf = concrete.node_tree.nodes.get("Principled BSDF")
pbsdf.inputs["Base Color"].default_value = (0.62, 0.62, 0.62, 1)
pbsdf.inputs["Roughness"].default_value = 0.65
building.data.materials.append(concrete)

bpy.ops.object.light_add(type="SUN", location=(20, -20, 30))
sun = bpy.context.object
sun.data.energy = 4.0

bpy.ops.object.camera_add(location=(32, -32, 18))
cam = bpy.context.object
scene.camera = cam

cam.rotation_euler = (math.radians(65), 0, math.radians(45))
cam.keyframe_insert(data_path="location", frame=1)
cam.keyframe_insert(data_path="rotation_euler", frame=1)

cam.location = (-32, 32, 18)
cam.rotation_euler = (math.radians(65), 0, math.radians(-135))
cam.keyframe_insert(data_path="location", frame=90)
cam.keyframe_insert(data_path="rotation_euler", frame=90)

cam.location = (32, -32, 18)
cam.rotation_euler = (math.radians(65), 0, math.radians(45))
cam.keyframe_insert(data_path="location", frame=180)
cam.keyframe_insert(data_path="rotation_euler", frame=180)

bpy.ops.render.render(animation=True)
