FROM docker-registry.amirmuz.com/python:3.12-alpine
WORKDIR /app
COPY server.py .
RUN pip install flask
CMD ["python3", "server.py"]
