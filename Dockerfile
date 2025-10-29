# FROM docker-registry.amirmuz.com/python:3.12-alpine
# WORKDIR /app
# COPY server.py .
# RUN pip install flask
# CMD ["python3", "server.py"]

# ================================
# PyMonNet Leader-Aware Server
# ================================
FROM python:3.11-slim

WORKDIR /app
COPY server.py /app/

# Install Docker CLI (for leader detection) + Flask
RUN apt-get update && apt-get install -y docker-cli procps && \
    pip install flask requests && \
    rm -rf /var/lib/apt/lists/*

# Run in unbuffered mode for real-time logs
CMD ["python3", "-u", "server.py"]
