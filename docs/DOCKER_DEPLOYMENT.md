# Docker Deployment

This app can run as one Docker container with SQLite, logs, and uploaded media stored in Docker volumes.

## Build and Start

1. Copy the example environment file:
   ```bash
   cp .env.docker.example .env
   ```

2. Edit `.env`:
   - Set a strong `SECRET_KEY`.
   - Set `ALLOWED_HOSTS` to the server IP/hostname.
   - Set `CSRF_TRUSTED_ORIGINS` to the exact browser URLs users will use.
   - Change `TIMEMASTER_HOST_PORT` if another service already uses port `8000`.

3. Start the service:
   ```bash
   docker compose up -d --build
   ```

4. Create the first admin user:
   ```bash
   docker compose exec timemaster python manage.py createsuperuser
   ```

The app is available at `http://<server-ip>:<TIMEMASTER_HOST_PORT>/timesheet/`.

## Persistent Data

The compose file creates these named volumes:

- `timemaster_data`: SQLite database at `/app/data/db.sqlite3`
- `timemaster_media`: uploaded files at `/app/media`
- `timemaster_logs`: application log files at `/app/logs`

Migrations run automatically every time the container starts.

## Useful Commands

```bash
docker compose logs -f timemaster
docker compose restart timemaster
docker compose exec timemaster python manage.py shell
docker compose exec timemaster python manage.py dumpdata > backup.json
docker compose down
```

## Running Beside Other Container Services

Use a unique `TIMEMASTER_HOST_PORT` in `.env`, for example:

```env
TIMEMASTER_HOST_PORT=8010
ALLOWED_HOSTS=192.168.1.100 timemaster.company.local
CSRF_TRUSTED_ORIGINS=http://192.168.1.100:8010 http://timemaster.company.local:8010
```

If you already run a reverse proxy such as nginx, Caddy, or Traefik on the host, point it to `timemaster:8000` on a shared Docker network or to `127.0.0.1:<TIMEMASTER_HOST_PORT>` from the host.
