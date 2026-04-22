from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import os
import subprocess
import uuid

app = FastAPI(title="CONSIA Render Engine", version="1.0.0")

BASE_DIR = Path(__file__).resolve().parent
RENDER_PATH = Path("/workspace/renders")
RENDER_PATH.mkdir(parents=True, exist_ok=True)

BLENDER_BIN = os.getenv("BLENDER_BIN", "blender")
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")


class ProjectRequest(BaseModel):
    name: str = Field(..., min_length=1)
    floors: int = Field(default=12, ge=1, le=120)
    prompt: str = Field(..., min_length=3)


def check_auth(authorization: str | None):
    if not RENDER_API_KEY:
        return
    expected = f"Bearer {RENDER_API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def run_blender(script_name: str, output_file: str, prompt: str):
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        raise RuntimeError(f"missing_script: {script_path}")

    cmd = [
        BLENDER_BIN,
        "-b",
        "-P",
        str(script_path),
        "--",
        output_file,
        prompt
    ]

    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True
    )

    if completed.returncode != 0:
        raise RuntimeError(
            f"blender_failed: script={script_name}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


@app.get("/")
def root():
    return {
        "ok": True,
        "system": "CONSIA_RENDER_ENGINE",
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
            timeout=10,
            check=False,
        )
    except Exception:
        blender_ok = False

    return {
        "ok": True,
        "system": "CONSIA_RENDER_ENGINE",
        "blender_bin": BLENDER_BIN,
        "blender_ok": blender_ok,
        "render_path": str(RENDER_PATH),
    }


@app.post("/full")
def full(payload: ProjectRequest, authorization: str | None = Header(default=None)):
    check_auth(authorization)

    pid = str(uuid.uuid4())
    image_file = str(RENDER_PATH / f"{pid}.png")
    video_file = str(RENDER_PATH / f"{pid}.mp4")

    try:
        run_blender("scene_exterior.py", image_file, payload.prompt)
        run_blender("scene_video.py", video_file, payload.prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "ok": True,
        "project_id": pid,
        "status": "completed",
        "image": image_file,
        "video": video_file
    }
