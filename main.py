from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import subprocess
import uuid
import os
from pathlib import Path

app = FastAPI(title="CONSIA Render Engine")

RENDER_PATH = Path("/workspace/renders")
BLENDER_BIN = os.getenv("BLENDER_BIN", "blender")
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")

class ProjectRequest(BaseModel):
    name: str = Field(..., min_length=1)
    floors: int = Field(default=12, ge=1, le=120)
    prompt: str = Field(..., min_length=3)

@app.get("/health")
def health():
    return {
        "ok": True,
        "system": "CONSIA_RENDER_ENGINE",
        "blender_bin": BLENDER_BIN,
        "render_path": str(RENDER_PATH)
    }

@app.post("/full")
def full(payload: ProjectRequest, authorization: str | None = Header(default=None)):
    if RENDER_API_KEY:
        expected = f"Bearer {RENDER_API_KEY}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="unauthorized")

    RENDER_PATH.mkdir(parents=True, exist_ok=True)

    pid = str(uuid.uuid4())
    image_out = RENDER_PATH / f"{pid}.png"
    video_out = RENDER_PATH / f"{pid}.mp4"

    run_blender("scene_exterior.py", str(image_out), payload.prompt)
    run_blender("scene_video.py", str(video_out), payload.prompt)

    return {
        "ok": True,
        "project_id": pid,
        "image": f"/renders/{pid}.png",
        "video": f"/renders/{pid}.mp4"
    }

def run_blender(script_name: str, output_file: str, prompt: str):
    cmd = [
        BLENDER_BIN,
        "-b",
        "-P",
        script_name,
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
            f"blender_failed: script={script_name} stdout={completed.stdout} stderr={completed.stderr}"
        )
