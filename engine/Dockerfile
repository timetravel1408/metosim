FROM nvidia/cuda:12.3.1-runtime-ubuntu22.04

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3-pip python3.11-venv && \
    rm -rf /var/lib/apt/lists/*

COPY setup.cfg pyproject.toml ./
RUN pip install --no-cache-dir ".[engine]"

COPY engine/ ./engine/

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

CMD ["python3", "-m", "metosim_engine.runner"]
