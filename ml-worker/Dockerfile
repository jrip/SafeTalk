FROM python:3.12-slim

WORKDIR /workspace
ENV PYTHONPATH=/workspace

COPY ml-worker /workspace/ml-worker
RUN pip install --no-cache-dir -r /workspace/ml-worker/requirements.txt

CMD ["python", "/workspace/ml-worker/main.py"]
