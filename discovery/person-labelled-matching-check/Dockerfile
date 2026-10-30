FROM python:3.12-slim
WORKDIR /app
COPY method/requirements.txt method/requirements.txt
RUN pip install --no-cache-dir -r method/requirements.txt
COPY method ./method
COPY labelling ./labelling
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/method
CMD ["python", "method/run.py"]
