FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

RUN apt-get update && apt-get install -y blender && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY main.py /workspace/main.py
COPY scene_exterior.py /workspace/scene_exterior.py
COPY scene_video.py /workspace/scene_video.py

RUN pip install --no-cache-dir fastapi uvicorn pydantic

ENV BLENDER_BIN=blender
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
