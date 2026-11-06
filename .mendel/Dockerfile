# Build targets that bring this application's SQLite database up to date, and report on it.
# Build from the repository root:  docker build -f .mendel/Dockerfile --target migrate .
# These are the files that, when changed, mean this file should be written again.
# depends-on: pairing_site/db.py pairing_site/config.py

# The application keeps all of its records in one SQLite file. Its migrations are the numbered SQL files in
# pairing_site/migrations/, applied in order by db.migrate() and recorded in the schema_migrations table.
# This stage runs that same function. It picks the database the way the application does, copied from
# pairing_site/config.py (database_path) and pairing_site/db.py (connect): the DATABASE_PATH environment
# variable, with no default and no config file. SQLite is part of Python's standard library, so only the
# modules that function needs are copied and nothing is installed. Same base image as the application's own.
#
# The stage runs as root, as the application's container does at start: the file lives on a disk that may be
# mounted owned by root, and start.sh hands that folder to the app user when the application starts.
FROM python:3.12-slim AS migrate
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
COPY pairing_site/__init__.py pairing_site/config.py pairing_site/db.py ./pairing_site/
COPY pairing_site/migrations/ ./pairing_site/migrations/
# Applies every outstanding migration and exits 0 (also when none is outstanding). A failure, or a missing
# DATABASE_PATH, prints the error and exits 1.
CMD ["python", "-c", "from pairing_site import db; done = db.migrate(); print('applied: ' + (', '.join(done) or 'nothing, the schema is up to date'))"]

# Reports the application's stores, and rehearses and applies migrations. Source: .mendel/phase/.
FROM migrate AS adapter
COPY .mendel/phase/phase /mendel/phase
RUN chmod 755 /mendel/phase
