FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE=/workspace

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
        mavsdk==3.0.0 \
        pydantic==2.10.0 \
        openai==1.55.0 \
        opencv-python-headless==4.10.0.84 \
        numpy==1.26.4 \
        requests==2.32.0 \
        fastapi==0.115.0 \
        uvicorn==0.32.0 \
        pymavlink==2.4.43

RUN pip install --no-cache-dir ultralytics==8.3.0

RUN curl -fsSL https://ollama.com/install.sh | bash

RUN mkdir -p ${WORKSPACE}

WORKDIR ${WORKSPACE}
CMD ["bash"]
