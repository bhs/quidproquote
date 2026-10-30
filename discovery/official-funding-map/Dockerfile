FROM python:3.12-slim
WORKDIR /app
COPY fmap_lib.py collect.py collect_pages.py build_map.py picks.json funding-map.md ./
COPY data ./data
COPY tests ./tests
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "python collect.py && python build_map.py"]
