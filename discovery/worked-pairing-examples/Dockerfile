FROM python:3.12-slim
WORKDIR /app
COPY trial_lib.py compare_lib.py pairing_lib.py money.py build_pairings.py picks.json ./
COPY data ./data
COPY tests ./tests
ENV PYTHONUNBUFFERED=1
CMD ["python", "build_pairings.py"]
