from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import uuid
import subprocess
import threading
import os

app = FastAPI(title="CONSIA Render Engine")

RENDER_PATH = Path("/workspace/renders")
RENDER_PATH.mkdir(parents=True, exist_ok=True)

BLENDER_BIN = os.getenv("BLENDER_BIN", "blender")


class ProjectRequest(BaseModel):
    name: str = Field(..., min_length=1)
    floors: int = Field(default=12)
    prompt: str = Field(..., min_length=3)


# =========================
# RENDER REAL CON BLENDER
# =========================
def run_render(project_dir, prompt):
    try:
        output_file = project_dir / "render.png"

        # Script Blender dinámico
        script = f"""
import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)

bpy.ops.mesh.primitive_cube_add(size=2)
cube = bpy.context.active_object

cube.scale = (1, 1, 3)

light_data = bpy.data.lights.new(name="light", type='SUN')
light_object = bpy.data.objects.new(name="light", object_data=light_data)
bpy.context.collection.objects.link(light_object)
light_object.location = (5, 5, 10)

camera_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", camera_data)
bpy.context.collection.objects.link(camera)
camera.location = (7, -7, 5)
camera.rotation_euler = (1.1, 0, 0.8)
bpy.context.scene.camera = camera

bpy.context.scene.render.filepath = "{output_file}"
bpy.context.scene.render.image_settings.file_format = 'PNG'

bpy.ops.render.render(write_still=True)
"""

        script_path = project_dir / "render.py"
        script_path.write_text(script)

        subprocess.run([
            BLENDER_BIN,
            "-b",
            "--python", str(script_path)
        ])

        (project_dir / "result.json").write_text(f'''
{{
    "ok": true,
    "status": "completed",
    "image": "{output_file}"
}}
''')

    except Exception as e:
        (project_dir / "result.json").write_text(f'''
{{
    "ok": false,
    "error": "{str(e)}"
}}
''')


# =========================
# ENDPOINTS
# =========================
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/full")
def full(data: ProjectRequest):
    project_id = str(uuid.uuid4())
    project_dir = RENDER_PATH / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    (project_dir / "prompt.txt").write_text(data.prompt)

    # render en background
    threading.Thread(
        target=run_render,
        args=(project_dir, data.prompt),
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
        raise HTTPException(404)

    files = [f.name for f in project_dir.iterdir()]

    return {
        "ok": True,
        "project_id": project_id,
        "files": files
    }


@app.get("/projects/{project_id}/result")
def get_result(project_id: str):
    project_dir = RENDER_PATH / project_id
    result_file = project_dir / "result.json"

    if not result_file.exists():
        raise HTTPException(404, "result_not_ready")

    return {
        "ok": True,
        "result": result_file.read_text()
    }
