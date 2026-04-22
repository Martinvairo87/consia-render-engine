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
scene.cycles.samples = 16
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.filepath = output

# piso
bpy.ops.mesh.primitive_plane_add(size=100, location=(0, 0, 0))

# edificio simple
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 6))
building = bpy.context.object
building.scale = (4, 4, 6)

# material
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

# cámara
bpy.ops.object.camera_add(location=(18, -18, 10))
cam = bpy.context.object
cam.rotation_euler = (math.radians(65), 0, math.radians(45))
scene.camera = cam

bpy.ops.render.render(write_still=True)
