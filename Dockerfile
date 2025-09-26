FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/dagster/app

# Copy pipeline code
COPY pipelines/setup.py .
COPY pipelines/hello_world_pipeline ./hello_world_pipeline

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Set the default command
CMD ["dagster", "code-server", "start", "-h", "0.0.0.0", "-p", "3030", "-m", "hello_world_pipeline.definitions"]
