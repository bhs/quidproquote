# Build targets that bring this application's persistent stores up to date and report on them.
# Build from the repository root:  docker build -f .mendel/Dockerfile --target migrate .
# These are the files that, when changed, mean this file should be written again.
# depends-on:

# This application keeps no durable state: it has no database, no migration tooling, and no
# connection setting of any kind (its settings are FF_* variables for how a run reads and
# caches meetings, and none of them names a store). So there is nothing for this stage to
# select a database with, and nothing to copy from the application's image.
FROM alpine:3.24 AS migrate
CMD ["echo", "This application has no persistent stores to migrate."]

# Reports the stores this application has (none) as JSON on stdout. Source: .mendel/phase/.
FROM migrate AS adapter
COPY .mendel/phase/phase /mendel/phase
RUN chmod 755 /mendel/phase
