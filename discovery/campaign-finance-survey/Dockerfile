FROM python:3.12-slim
WORKDIR /app
COPY survey_lib.py calaccess.py profile.py ./
COPY tests ./tests
ENV PYTHONUNBUFFERED=1
CMD ["python", "profile.py"]
