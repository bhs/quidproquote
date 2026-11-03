FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY fmap_lib.py ff_lib.py legistar.py report.py run.py ./
COPY data ./data
COPY tests ./tests
ENV PYTHONUNBUFFERED=1
CMD ["python", "run.py"]
