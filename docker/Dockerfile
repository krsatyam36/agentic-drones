FROM osrf/ros:humble-desktop

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV WORKSPACE=/workspace

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-venv \
    python3-colcon-common-extensions \
    git \
    wget \
    curl \
    zstd \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip && \
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

# Pre-install sympy from pip to avoid distutils conflict with torch
RUN pip install --no-cache-dir --ignore-installed sympy==1.14.0

# PX4 build dependencies
RUN pip install --no-cache-dir kconfiglib jinja2 pyros-genmsg jsonschema

RUN curl -fsSL https://ollama.com/install.sh | bash

# Bake ultralytics into the image (avoids 20-min runtime install every container start)
RUN pip install --no-cache-dir --ignore-installed ultralytics==8.3.0

RUN mkdir -p ${WORKSPACE}

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc && \
    echo "export PX4_HOME_LAT=47.397742" >> ~/.bashrc && \
    echo "export PX4_HOME_LON=8.545594" >> ~/.bashrc

WORKDIR ${WORKSPACE}
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
