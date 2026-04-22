import bpy
import sys
import math

argv = sys.argv
argv = argv[argv.index("--") + 1:]

output = argv[0]
prompt = argv[1] if len(argv) > 1 else "modern tower"

bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 8
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 24
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.filepath = output

# piso
bpy.ops.mesh.primitive_plane_add(size=100, location=(0, 0, 0))

# edificio
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 6))
building = bpy.context.object
building.scale = (4, 4, 6)

mat = bpy.data.materials.new(name="BuildingMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.7, 0.7, 0.75, 1.0)
bsdf.inputs["Roughness"].default_value = 0.4
building.data.materials.append(mat)

# luz
bpy.ops.object.light_add(type="SUN", location=(10, -10, 20))
sun = bpy.context.object
sun.data.energy = 3.0

# cámara con movimiento simple
bpy.ops.object.camera_add(location=(18, -18, 10))
cam = bpy.context.object
scene.camera = cam

cam.rotation_euler = (math.radians(65), 0, math.radians(45))
cam.keyframe_insert(data_path="location", frame=1)
cam.keyframe_insert(data_path="rotation_euler", frame=1)

cam.location = (18, 18, 10)
cam.rotation_euler = (math.radians(65), 0, math.radians(135))
cam.keyframe_insert(data_path="location", frame=24)
cam.keyframe_insert(data_path="rotation_euler", frame=24)

bpy.ops.render.render(animation=True)
