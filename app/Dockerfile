FROM python:3.12-slim

WORKDIR /workspace
ENV PYTHONPATH=/workspace

COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY app /workspace/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
