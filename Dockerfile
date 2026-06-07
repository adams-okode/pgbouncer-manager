FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY cli/ ./cli/

# Expose port
EXPOSE 3000

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
