from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
import uuid
import subprocess
import threading
import os
import json
from datetime import datetime

app = FastAPI(title="CONSIA Render Engine")

RENDER_PATH = Path("/workspace/renders")
RENDER_PATH.mkdir(parents=True, exist_ok=True)

BLENDER_BIN = os.getenv("BLENDER_BIN", "blender")


class ProjectRequest(BaseModel):
    name: str = Field(..., min_length=1)
    floors: int = Field(default=12, ge=1, le=120)
    prompt: str = Field(..., min_length=3)


def write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def run_render(project_id: str, project_dir: Path, data: ProjectRequest):
    result_file = project_dir / "result.json"
    prompt_file = project_dir / "prompt.txt"
    script_file = project_dir / "render.py"
    image_file = project_dir / "render.png"
    log_file = project_dir / "render.log"

    try:
        prompt_file.write_text(data.prompt, encoding="utf-8")

        write_json(result_file, {
            "ok": True,
            "project_id": project_id,
            "status": "processing",
            "name": data.name,
            "floors": data.floors,
            "prompt": data.prompt,
            "image_file": str(image_file),
            "started_at": datetime.utcnow().isoformat() + "Z"
        })

        blender_script = f'''
import bpy

OUTPUT_PATH = r"{str(image_file)}"

bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.image_settings.file_format = 'PNG'

# WORLD FIX
if bpy.context.scene.world is None:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
else:
    world = bpy.context.scene.world

world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg is None:
    bg = world.node_tree.nodes.new(type="ShaderNodeBackground")

bg.inputs[0].default_value = (0.92, 0.95, 1.0, 1.0)
bg.inputs[1].default_value = 0.8

# GROUND
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
ground = bpy.context.active_object

mat = bpy.data.materials.new("GroundMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.8, 0.82, 0.85, 1)
ground.data.materials.append(mat)

# BUILDING
h = max({data.floors} * 0.35, 3)

bpy.ops.mesh.primitive_cube_add(location=(0, 0, h))
tower = bpy.context.active_object
tower.scale = (2.5, 1.8, h)

mat = bpy.data.materials.new("TowerMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.7, 0.75, 0.8, 1)
bsdf.inputs["Roughness"].default_value = 0.5
tower.data.materials.append(mat)

# GLASS
bpy.ops.mesh.primitive_cube_add(location=(2.6, 0, h))
glass = bpy.context.active_object
glass.scale = (0.05, 1.7, h * 0.95)

mat = bpy.data.materials.new("GlassMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]

if "Transmission" in bsdf.inputs:
    bsdf.inputs["Transmission"].default_value = 1.0

bsdf.inputs["Base Color"].default_value = (0.6, 0.8, 1.0, 1)
bsdf.inputs["Roughness"].default_value = 0.05

glass.data.materials.append(mat)

# LIGHT
light_data = bpy.data.lights.new(name="sun", type='SUN')
light = bpy.data.objects.new(name="sun", object_data=light_data)
bpy.context.collection.objects.link(light)
light.location = (10, -10, 15)

# CAMERA
bpy.ops.object.camera_add(location=(10, -12, 10))
cam = bpy.context.active_object
cam.rotation_euler = (1.1, 0, 0.9)
scene.camera = cam

# RENDER
scene.render.filepath = OUTPUT_PATH
bpy.ops.render.render(write_still=True)
'''

        script_file.write_text(blender_script)

        with open(log_file, "w") as log:
            subprocess.run(
                [BLENDER_BIN, "--background", "--python", str(script_file)],
                stdout=log,
                stderr=log
            )

        if not image_file.exists():
            raise Exception("image_not_generated")

        write_json(result_file, {
            "ok": True,
            "project_id": project_id,
            "status": "completed",
            "image": str(image_file)
        })

    except Exception as e:
        write_json(result_file, {
            "ok": False,
            "project_id": project_id,
            "status": "failed",
            "error": str(e)
        })


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/full")
def full(data: ProjectRequest):
    project_id = str(uuid.uuid4())
    project_dir = RENDER_PATH / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    threading.Thread(
        target=run_render,
        args=(project_id, project_dir, data),
        daemon=True
    ).start()

    return {
        "ok": True,
        "project_id": project_id,
        "status": "render_started"
    }


@app.get("/projects/{project_id}")
def get_project(project_id: str):
    project_dir = RENDER_PATH / project_id
    if not project_dir.exists():
        raise HTTPException(404, "not_found")

    return {
        "ok": True,
        "project_id": project_id,
        "files": [p.name for p in project_dir.iterdir()]
    }


@app.get("/projects/{project_id}/image")
def get_image(project_id: str):
    file = RENDER_PATH / project_id / "render.png"
    if not file.exists():
        raise HTTPException(404, "image_not_ready")
    return FileResponse(file)


@app.get("/projects/{project_id}/result")
def get_result(project_id: str):
    file = RENDER_PATH / project_id / "result.json"
    if not file.exists():
        raise HTTPException(404)
    return json.loads(file.read_text())


@app.get("/projects/{project_id}/log")
def get_log(project_id: str):
    file = RENDER_PATH / project_id / "render.log"
    if not file.exists():
        return {"log": ""}
    return {"log": file.read_text()}
