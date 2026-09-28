# ADR 0002: SQLite instead of PostgreSQL

Accepted for the local single-operator release. SQLite WAL, transactional writes and read-only connections support immutable runs without a third required container or database credentials. This keeps Docker and native development small. It is not a multi-writer cloud architecture. PostgreSQL, migrations, background jobs and row-level tenancy belong in a later scaling effort.
