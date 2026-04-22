from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import uuid
import os
import subprocess
import threading
import traceback
from datetime import datetime

# =========================
# CONFIG
# =========================
app = FastAPI(title="CONSIA Render Engine")

RENDER_PATH = Path("/workspace/renders")
RENDER_PATH.mkdir(parents=True, exist_ok=True)

BLENDER_BIN = os.getenv("BLENDER_BIN", "blender")
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")

# =========================
# MODELO
# =========================
class ProjectRequest(BaseModel):
    name: str = Field(..., min_length=1)
    floors: int = Field(default=12, ge=1, le=120)
    prompt: str = Field(..., min_length=3)

# =========================
# UTIL LOG
# =========================
def log(project_dir, message):
    log_file = project_dir / "log.txt"
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now()}] {message}\n")

# =========================
# MOTOR RENDER (BACKGROUND)
# =========================
def run_render(project_dir, prompt_file, result_file):
    try:
        log(project_dir, "START RENDER")

        # 🔥 SIMULACIÓN (reemplazable por Blender real)
        prompt = prompt_file.read_text()

        result_file.write_text(
            f"""
            {{
                "result": "render_ok",
                "prompt": "{prompt}",
                "status": "completed"
            }}
            """,
            encoding="utf-8"
        )

        log(project_dir, "RENDER COMPLETED")

        # ======================
        # 🔥 PARA USAR BLENDER REAL
        # DESCOMENTAR ↓↓↓
        # ======================
        """
        subprocess.run([
            BLENDER_BIN,
            "-b",
            "-noaudio",
            "--python", "render.py",
            "--",
            str(prompt_file),
            str(result_file)
        ])
        """

    except Exception as e:
        log(project_dir, f"ERROR: {str(e)}")
        traceback.print_exc()

# =========================
# ENDPOINTS
# =========================

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

# =========================
# CREAR RENDER
# =========================
@app.post("/full")
def full(data: ProjectRequest):

    try:
        project_id = str(uuid.uuid4())
        project_dir = RENDER_PATH / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        prompt_file = project_dir / "prompt.txt"
        result_file = project_dir / "result.json"

        prompt_file.write_text(data.prompt, encoding="utf-8")

        # 🔥 BACKGROUND (CLAVE PARA NO 500)
        threading.Thread(
            target=run_render,
            args=(project_dir, prompt_file, result_file),
            daemon=True
        ).start()

        return {
            "ok": True,
            "project_id": project_id,
            "status": "render_started",
            "name": data.name,
            "floors": data.floors
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"render_engine_error: {str(e)}")

# =========================
# VER ESTADO
# =========================
@app.get("/projects/{project_id}")
def get_project(project_id: str, authorization: str | None = Header(default=None)):

    if RENDER_API_KEY:
        token = (authorization or "").replace("Bearer ", "").strip()
        if token != RENDER_API_KEY:
            raise HTTPException(status_code=401, detail="unauthorized")

    project_dir = RENDER_PATH / project_id

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="project_not_found")

    files = [f.name for f in project_dir.iterdir()]

    result_file = project_dir / "result.json"

    status = "processing"
    result_data = None

    if result_file.exists():
        status = "completed"
        result_data = result_file.read_text()

    return {
        "ok": True,
        "project_id": project_id,
        "status": status,
        "files": files,
        "result": result_data
    }

# =========================
# DESCARGAR RESULTADO
# =========================
@app.get("/projects/{project_id}/result")
def get_result(project_id: str):

    project_dir = RENDER_PATH / project_id
    result_file = project_dir / "result.json"

    if not result_file.exists():
        raise HTTPException(status_code=404, detail="result_not_ready")

    return {
        "ok": True,
        "result": result_file.read_text()
    }
