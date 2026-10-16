FROM python:3.10-slim

# Install system dependencies required for OpenCV, Open3D, and PyTorch (C++ bindings)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies with CPU-optimized PyTorch wheels (reduces image size from ~5GB to ~600MB)
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Copy source code
COPY . .

# Run worker by default
CMD ["python", "-m", "pipeline.pipeline_orchestrator"]
