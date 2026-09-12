# ==============================================================================
# CatalogX Backend Dockerfile
# Build context must be the root of the repo (UNI-HACK/)
# ==============================================================================

# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for compiling python packages and WeasyPrint rendering)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy both requirements files
COPY DEV/backend/requirements.txt ./requirements-backend.txt
COPY AI-ML/requirements.txt ./requirements-aiml.txt

# Install Python dependencies (backend + AI-ML)
RUN pip install --no-cache-dir -r requirements-backend.txt -r requirements-aiml.txt

# Copy the AI-ML directory (needed by backend pipeline)
COPY AI-ML/ ./AI-ML/

# Copy the backend code
COPY DEV/backend/ ./DEV/backend/

# Ensure the app structure aligns with Python imports
ENV PYTHONPATH=/app/DEV/backend:/app
ENV PYTHONUNBUFFERED=1

# Expose FastAPI port
EXPOSE 8000

# Run the FastAPI application using Uvicorn
WORKDIR /app/DEV/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
