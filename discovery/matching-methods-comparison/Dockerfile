FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY trial_lib.py compare_lib.py embed.py judge.py money.py report.py render.py compare.py ./
COPY data ./data
COPY tests ./tests
ENV PYTHONUNBUFFERED=1
CMD ["python", "compare.py"]
