FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV BLENDER_BIN=blender

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    blender \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY main.py /workspace/main.py
COPY scene_exterior.py /workspace/scene_exterior.py
COPY scene_video.py /workspace/scene_video.py

RUN pip3 install --no-cache-dir fastapi uvicorn pydantic

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
