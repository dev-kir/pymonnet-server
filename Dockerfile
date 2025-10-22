FROM docker-registry.amirmuz.com/python:3.12-alpine
WORKDIR /app
COPY manager_server.py .
RUN pip install flask
CMD ["python3", "manager_server.py"]
