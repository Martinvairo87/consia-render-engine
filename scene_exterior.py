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
scene.cycles.samples = 128
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.filepath = output

bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 12))
building = bpy.context.object
building.scale = (6, 6, 12)

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, -5.8, 12))
glass = bpy.context.object
glass.scale = (5.5, 0.1, 10)

glass_mat = bpy.data.materials.new(name="Glass")
glass_mat.use_nodes = True
bsdf = glass_mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Transmission"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.03
glass.data.materials.append(glass_mat)

concrete = bpy.data.materials.new(name="Concrete")
concrete.use_nodes = True
pbsdf = concrete.node_tree.nodes.get("Principled BSDF")
pbsdf.inputs["Base Color"].default_value = (0.62, 0.62, 0.62, 1)
pbsdf.inputs["Roughness"].default_value = 0.65
building.data.materials.append(concrete)

bpy.ops.object.light_add(type="SUN", location=(20, -20, 30))
sun = bpy.context.object
sun.data.energy = 4.0

bpy.ops.object.camera_add(location=(28, -28, 18))
cam = bpy.context.object
cam.rotation_euler = (math.radians(62), 0, math.radians(45))
scene.camera = cam

bpy.ops.render.render(write_still=True)
