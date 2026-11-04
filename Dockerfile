FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY pairing_site ./pairing_site
COPY tests ./tests
# The SQLite file lives under /data, the directory that is kept between restarts.
RUN mkdir -p /data
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/' % os.environ.get('PORT', '8080'), timeout=4)"]
# One worker: the daily fetch runs as a thread inside it, and the records are one SQLite file.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 120 pairing_site.wsgi:app"]
