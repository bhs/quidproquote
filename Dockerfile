FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8080
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The discovery libraries the site reuses, and the survey data the seed and the worker start from.
COPY discovery/official-funding-map/fmap_lib.py discovery/official-funding-map/pairing_cards.py \
     discovery/official-funding-map/collect.py discovery/official-funding-map/build_map.py \
     discovery/official-funding-map/picks.json /app/discovery/official-funding-map/
COPY discovery/official-funding-map/data /app/discovery/official-funding-map/data
COPY discovery/funder-first-pairings/ff_lib.py discovery/funder-first-pairings/legistar.py /app/discovery/funder-first-pairings/
COPY discovery/funder-first-pairings/data/subjects.json discovery/funder-first-pairings/data/reviews.json /app/discovery/funder-first-pairings/data/
COPY discovery/matching-methods-comparison/judge.py discovery/matching-methods-comparison/trial_lib.py /app/discovery/matching-methods-comparison/

COPY pairing_site ./pairing_site
COPY tests ./tests
COPY start.sh ./start.sh

# The database is one SQLite file under /data, the directory the attached disk is mounted on; the site and the
# worker both open it. The process runs as root because a freshly attached disk is owned by root.
RUN mkdir -p /data
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=6 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/' % os.environ.get('PORT','8080'), timeout=4)"
CMD ["./start.sh"]
