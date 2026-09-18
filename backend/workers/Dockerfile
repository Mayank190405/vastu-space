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

# Install Python dependencies
COPY requirements.txt .
# We use no-cache-dir to keep the image size down
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run pytest by default
CMD ["pytest", ".", "-v"]
