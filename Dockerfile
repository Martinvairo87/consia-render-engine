FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    blender \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY . .

RUN pip install --no-cache-dir fastapi uvicorn pydantic

ENV BLENDER_BIN=blender

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
