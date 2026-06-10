# Docker / Railway deployment notes

Quick steps to deploy the `backend` service to Railway using the Dockerfile in this folder:

1. Push this repo to GitHub (or connect your existing repo) and connect it to Railway.
2. In Railway, create a new project and link the repository. Railway will detect the `Dockerfile` and build the image.
3. Set the following environment variables in Railway (Project > Settings > Variables):
   - `SECRET_KEY` (production Django secret)
   - `DEBUG` = `False`
   - `DATABASE_URL` (e.g. PostgreSQL managed by Railway)
   - `REDIS_URL` (for Celery broker + cache)
   - `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` (if using Stripe)
   - Any other `FRONTEND_URL`, `VINAUDIT_API_KEY`, etc.
4. Railway exposes the service port in the `PORT` environment variable. The Dockerfile command uses `$PORT`.
5. (Optional) If you need a worker, add a separate Railway service using the same image, but set the start command to:

```
celery -A vin_project worker --loglevel=info --concurrency 2
```

Notes:

- The image installs system packages required for `psycopg2` and similar wheels. If you prefer a slimmer build, consider using `psycopg2-binary` or a multi-stage build.
- The Dockerfile runs `collectstatic` at build time; if static files depend on runtime settings, adjust as needed.
