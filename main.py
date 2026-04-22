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
import math

OUTPUT_PATH = r"{str(image_file)}"

# Reset total
bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'

# World
world = bpy.data.worlds["World"]
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.92, 0.95, 1.0, 1.0)
bg.inputs[1].default_value = 0.9

# Ground
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

ground_mat = bpy.data.materials.new(name="GroundMat")
ground_mat.use_nodes = True
bsdf = ground_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.78, 0.80, 0.82, 1.0)
bsdf.inputs["Roughness"].default_value = 0.95
ground.data.materials.append(ground_mat)

# Building base
bpy.ops.mesh.primitive_cube_add(location=(0, 0, {max(data.floors * 0.35, 2.5)}))
tower = bpy.context.active_object
tower.name = "Tower"
tower.scale = (2.6, 1.8, max({data.floors} * 0.35, 2.5))

tower_mat = bpy.data.materials.new(name="TowerMat")
tower_mat.use_nodes = True
bsdf = tower_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.72, 0.75, 0.78, 1.0)
bsdf.inputs["Roughness"].default_value = 0.55
bsdf.inputs["Metallic"].default_value = 0.08
tower.data.materials.append(tower_mat)

# Glass facade panel
bpy.ops.mesh.primitive_cube_add(location=(2.61, 0, max({data.floors} * 0.35, 2.5)))
glass = bpy.context.active_object
glass.name = "GlassFacade"
glass.scale = (0.06, 1.55, max({data.floors} * 0.33, 2.3))

glass_mat = bpy.data.materials.new(name="GlassMat")
glass_mat.use_nodes = True
bsdf = glass_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.55, 0.75, 0.95, 1.0)
bsdf.inputs["Transmission Weight"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.08
bsdf.inputs["IOR"].default_value = 1.45
glass.data.materials.append(glass_mat)

# Side volume
bpy.ops.mesh.primitive_cube_add(location=(-1.8, -2.0, max({data.floors} * 0.12, 1.2)))
side = bpy.context.active_object
side.name = "Podium"
side.scale = (1.8, 1.3, max({data.floors} * 0.12, 1.2))
side.data.materials.append(tower_mat)

# Sun light
sun_data = bpy.data.lights.new(name="Sun", type='SUN')
sun = bpy.data.objects.new(name="Sun", object_data=sun_data)
bpy.context.collection.objects.link(sun)
sun.location = (10, -10, 18)
sun.rotation_euler = (math.radians(50), 0, math.radians(35))
sun.data.energy = 3.2

# Area light
area_data = bpy.data.lights.new(name="Area", type='AREA')
area = bpy.data.objects.new(name="Area", object_data=area_data)
bpy.context.collection.objects.link(area)
area.location = (6, -4, 8)
area.rotation_euler = (math.radians(65), 0, math.radians(55))
area.data.energy = 3000
area.data.shape = 'RECTANGLE'
area.data.size = 8
area.data.size_y = 8

# Camera
cam_data = bpy.data.cameras.new(name="Camera")
cam = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (12, -14, 8)
cam.rotation_euler = (math.radians(68), 0, math.radians(40))
scene.camera = cam

# Small river plane for premium look
bpy.ops.mesh.primitive_plane_add(size=80, location=(18, 18, -0.02))
river = bpy.context.active_object
river.rotation_euler = (0, 0, math.radians(45))

river_mat = bpy.data.materials.new(name="RiverMat")
river_mat.use_nodes = True
bsdf = river_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.25, 0.45, 0.65, 1.0)
bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["Roughness"].default_value = 0.04
bsdf.inputs["Transmission Weight"].default_value = 0.15
river.data.materials.append(river_mat)

scene.render.filepath = OUTPUT_PATH
bpy.ops.render.render(write_still=True)
'''

        script_file.write_text(blender_script, encoding="utf-8")

        with open(log_file, "w", encoding="utf-8") as lf:
            process = subprocess.run(
                [BLENDER_BIN, "-b", "--python", str(script_file)],
                stdout=lf,
                stderr=lf,
                text=True
            )

        if process.returncode != 0:
            write_json(result_file, {
                "ok": False,
                "project_id": project_id,
                "status": "failed",
                "name": data.name,
                "floors": data.floors,
                "prompt": data.prompt,
                "error": "blender_render_failed",
                "log_file": str(log_file),
                "finished_at": datetime.utcnow().isoformat() + "Z"
            })
            return

        if not image_file.exists():
            write_json(result_file, {
                "ok": False,
                "project_id": project_id,
                "status": "failed",
                "name": data.name,
                "floors": data.floors,
                "prompt": data.prompt,
                "error": "image_not_generated",
                "log_file": str(log_file),
                "finished_at": datetime.utcnow().isoformat() + "Z"
            })
            return

        write_json(result_file, {
            "ok": True,
            "project_id": project_id,
            "status": "completed",
            "name": data.name,
            "floors": data.floors,
            "prompt": data.prompt,
            "image_file": str(image_file),
            "image_url": f"/projects/{project_id}/image",
            "log_file": str(log_file),
            "finished_at": datetime.utcnow().isoformat() + "Z"
        })

    except Exception as e:
        write_json(result_file, {
            "ok": False,
            "project_id": project_id,
            "status": "failed",
            "name": data.name,
            "floors": data.floors,
            "prompt": data.prompt,
            "error": str(e),
            "finished_at": datetime.utcnow().isoformat() + "Z"
        })


@app.get("/")
def root():
    return {
        "ok": True,
        "system": "CONSIA_RENDER_ENGINE",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/ping")
def ping():
    return {"ok": True, "status": "alive"}


@app.get("/health")
def health():
    return {
        "ok": True,
        "system": "CONSIA_RENDER_ENGINE",
        "blender_bin": BLENDER_BIN,
        "render_path": str(RENDER_PATH)
    }


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
        "status": "render_started",
        "name": data.name,
        "floors": data.floors,
        "prompt": data.prompt,
        "files": {
            "project_dir": str(project_dir),
            "prompt_file": str(project_dir / "prompt.txt"),
            "result_file": str(project_dir / "result.json")
        },
        "image_url": f"/projects/{project_id}/image",
        "result_url": f"/projects/{project_id}/result"
    }


@app.get("/projects/{project_id}")
def get_project(project_id: str):
    project_dir = RENDER_PATH / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="project_not_found")

    return {
        "ok": True,
        "project_id": project_id,
        "project_dir": str(project_dir),
        "files": sorted([p.name for p in project_dir.iterdir()])
    }


@app.get("/projects/{project_id}/result")
def get_result(project_id: str):
    project_dir = RENDER_PATH / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="project_not_found")

    result_file = project_dir / "result.json"
    if not result_file.exists():
        raise HTTPException(status_code=404, detail="result_not_ready")

    return json.loads(result_file.read_text(encoding="utf-8"))


@app.get("/projects/{project_id}/image")
def get_image(project_id: str):
    project_dir = RENDER_PATH / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="project_not_found")

    image_file = project_dir / "render.png"
    if not image_file.exists():
        raise HTTPException(status_code=404, detail="image_not_ready")

    return FileResponse(image_file, media_type="image/png", filename=f"{project_id}.png")


@app.get("/projects/{project_id}/log")
def get_log(project_id: str):
    project_dir = RENDER_PATH / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="project_not_found")

    log_file = project_dir / "render.log"
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="log_not_ready")

    return {
        "ok": True,
        "project_id": project_id,
        "log": log_file.read_text(encoding="utf-8")
    }
