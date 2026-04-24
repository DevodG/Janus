FROM python:3.11-slim

WORKDIR /app/backend

# Install only essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers if possible, but don't fail if it doesn't work
RUN playwright install --with-deps chromium 2>/dev/null || echo "Playwright installation failed, continuing..."

# Copy the application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/backend/app/data/context /app/backend/app/data/daemon /app/backend/app/data/adaptive /app/backend/app/data/knowledge /app/backend/app/data/memory /app/backend/app/data/simulations

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Expose port and run the application
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
