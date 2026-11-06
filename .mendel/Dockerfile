# Build targets that bring this application's Postgres database up to date, and report on it.
# Build from the repository root:  docker build -f .mendel/Dockerfile --target migrate .
# These are the files that, when changed, mean this file should be written again.
# depends-on: pairing_site/db.py pairing_site/config.py requirements.txt

# The application keeps all of its records in one Postgres database. Its migrations are the numbered SQL
# files in pairing_site/migrations/, applied in order by db.migrate() and recorded in schema_migrations.
# This stage runs that same function. It picks the database the way the application does, copied from
# pairing_site/config.py (database_url) and pairing_site/db.py (connect): the DATABASE_URL environment
# variable, with no default and no config file. Only the modules that function needs are copied, and only
# the psycopg driver is installed, at the version pinned in requirements.txt.
FROM python:3.12-slim AS migrate
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
COPY requirements.txt ./
RUN grep -E '^psycopg' requirements.txt > /tmp/driver.txt \
 && pip install --no-cache-dir -r /tmp/driver.txt \
 && rm /tmp/driver.txt
COPY pairing_site/__init__.py pairing_site/config.py pairing_site/db.py ./pairing_site/
COPY pairing_site/migrations/ ./pairing_site/migrations/
RUN useradd --create-home app && chown -R app /app
USER app
# Applies every outstanding migration and exits 0 (also when none is outstanding). A failure, or a missing
# DATABASE_URL, prints the error and exits 1.
CMD ["python", "-c", "from pairing_site import db; done = db.migrate(); print('applied: ' + (', '.join(done) or 'nothing, the schema is up to date'))"]

# Reports the application's stores, and rehearses and applies migrations. Source: .mendel/phase/.
FROM migrate AS adapter
USER root
COPY .mendel/phase/phase /mendel/phase
RUN chmod 755 /mendel/phase
USER app
