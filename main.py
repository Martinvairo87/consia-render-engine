from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import uuid
import os
from pathlib import Path

app = FastAPI(title="CONSIA Render Engine")

RENDER_PATH = Path("/workspace/renders")
BLENDER_BIN = os.getenv("BLENDER_BIN", "blender")
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")

RENDER_PATH.mkdir(parents=True, exist_ok=True)


class ProjectRequest(BaseModel):
    name: str = Field(..., min_length=1)
    floors: int = Field(default=12, ge=1, le=120)
    prompt: str = Field(..., min_length=3)


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
def full(data: ProjectRequest, authorization: str | None = Header(default=None)):
    try:
        if RENDER_API_KEY:
            token = (authorization or "").replace("Bearer ", "").strip()
            if token != RENDER_API_KEY:
                raise HTTPException(status_code=401, detail="unauthorized")

        project_id = str(uuid.uuid4())
        project_dir = RENDER_PATH / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        prompt_file = project_dir / "prompt.txt"
        result_file = project_dir / "result.json"

        prompt_file.write_text(data.prompt, encoding="utf-8")

        result_file.write_text(
            (
                "{\n"
                f'  "ok": true,\n'
                f'  "project_id": "{project_id}",\n'
                f'  "status": "render_started",\n'
                f'  "name": "{data.name}",\n'
                f'  "floors": {data.floors},\n'
                f'  "prompt_file": "{prompt_file}"\n'
                "}\n"
            ),
            encoding="utf-8"
        )

        return {
            "ok": True,
            "project_id": project_id,
            "status": "render_started",
            "name": data.name,
            "floors": data.floors,
            "prompt": data.prompt,
            "files": {
                "project_dir": str(project_dir),
                "prompt_file": str(prompt_file),
                "result_file": str(result_file)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"render_engine_error: {str(e)}")


@app.get("/projects/{project_id}")
def get_project(project_id: str, authorization: str | None = Header(default=None)):
    if RENDER_API_KEY:
        token = (authorization or "").replace("Bearer ", "").strip()
        if token != RENDER_API_KEY:
            raise HTTPException(status_code=401, detail="unauthorized")

    project_dir = RENDER_PATH / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="project_not_found")

    return {
        "ok": True,
        "project_id": project_id,
        "project_dir": str(project_dir),
        "files": [p.name for p in project_dir.iterdir()]
    }


@app.get("/projects/{project_id}/result")
def get_result(project_id: str, authorization: str | None = Header(default=None)):
    if RENDER_API_KEY:
        token = (authorization or "").replace("Bearer ", "").strip()
        if token != RENDER_API_KEY:
            raise HTTPException(status_code=401, detail="unauthorized")

    project_dir = RENDER_PATH / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="project_not_found")

    result_file = project_dir / "result.json"
    if not result_file.exists():
        raise HTTPException(status_code=404, detail="result_not_ready")

    return {
        "ok": True,
        "project_id": project_id,
        "result_file": str(result_file),
        "result": result_file.read_text(encoding="utf-8")
    }
