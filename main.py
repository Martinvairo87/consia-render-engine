from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import os
import subprocess
import uuid

app = FastAPI(title="CONSIA Render Engine", version="1.0.0")

RENDER_PATH = Path("/workspace/renders")
RENDER_PATH.mkdir(parents=True, exist_ok=True)

BLENDER_BIN = os.getenv("BLENDER_BIN", "blender")
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")


class ProjectRequest(BaseModel):
    name: str = Field(..., min_length=1)
    floors: int = Field(default=12, ge=1, le=120)
    prompt: str = Field(..., min_length=3)


def check_auth(x_api_key: str | None):
    if RENDER_API_KEY:
        if x_api_key != RENDER_API_KEY:
            raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def root():
    return {
        "ok": True,
        "system": "CONSIA Render Engine",
        "status": "running"
    }


@app.get("/ping")
def ping():
    return {
        "ok": True,
        "status": "alive"
    }


@app.get("/health")
def health():
    blender_ok = True
    try:
        subprocess.run(
            [BLENDER_BIN, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception:
        blender_ok = False

    return {
        "ok": True,
        "service": "consia-render-engine",
        "blender": blender_ok,
        "render_path": str(RENDER_PATH),
    }


@app.post("/render/project")
def render_project(req: ProjectRequest, x_api_key: str | None = Header(default=None)):
    check_auth(x_api_key)

    job_id = str(uuid.uuid4())
    output_file = RENDER_PATH / f"{job_id}.txt"

    output_file.write_text(
        f"CONSIA DEMO RENDER\n"
        f"name={req.name}\n"
        f"floors={req.floors}\n"
        f"prompt={req.prompt}\n",
        encoding="utf-8"
    )

    return {
        "ok": True,
        "job_id": job_id,
        "status": "completed",
        "output_file": str(output_file),
    }
