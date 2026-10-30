FROM python:3.12-slim
WORKDIR /app
COPY trial_lib.py analyze.py collect.py ./
COPY label_sample.json ./label_sample.json
COPY data ./data
COPY tests ./tests
ENV PYTHONUNBUFFERED=1
CMD ["python", "analyze.py"]
