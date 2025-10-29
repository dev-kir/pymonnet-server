# FROM docker-registry.amirmuz.com/python:3.12-alpine
# WORKDIR /app
# COPY server.py .
# RUN pip install flask
# CMD ["python3", "server.py"]

FROM python:3.11-slim

WORKDIR /app
COPY server.py /app/

RUN apt-get update && apt-get install -y docker-cli && \
    pip install flask requests && \
    rm -rf /var/lib/apt/lists/*

CMD ["python3", "server.py"]
