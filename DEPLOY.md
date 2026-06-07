# Deployment and Migration Guide

This document explains how to move from the local SQLite database to a managed production database (recommended), and how to migrate your existing data.

1) Provision a managed Postgres database
  - On Heroku: `heroku addons:create heroku-postgresql:hobby-dev`
  - On Render/AWS/GCP: create a Postgres instance and note the connection URL.

2) Set environment variables on the host
  - `DATABASE_URL`: Postgres connection string (e.g. `postgres://...` or `postgresql://...`)
  - `SECRET_KEY`: a secure random secret

3) Apply database migrations on the target DB

PowerShell:
```powershell
$env:FLASK_APP='app.py'
flask db upgrade
```

Linux/macOS:
```bash
export FLASK_APP=app.py
flask db upgrade
```

4) (Optional) Migrate data from local SQLite to Postgres
  - Ensure your local sqlite file exists at `instance/story_posts.db` (or set `SQLITE_PATH`).
  - Ensure `DATABASE_URL` or `TARGET_DATABASE_URL` points to the Postgres instance.
  - Run:

```bash
python scripts/migrate_sqlite_to_postgres.py
```

Notes:
- Always run `flask db upgrade` before the migration script so target tables exist.
- Back up your target DB before running the migration if it already contains data.
- After migration, restart your service and verify posts are present.

5) Ensure persistent storage
- Do not rely on SQLite files on ephemeral hosts. Use managed DBs or persistent volumes.
