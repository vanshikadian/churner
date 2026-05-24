# Deployment

This repo is ready for local development with `docker compose up --build`, but production should use the production Docker files in this repo instead of the dev server setup.

## Best Fit For This Repo

The simplest deployment path is a single Linux server or VM running Docker Compose:

- `frontend`: static React build served by Nginx on port `80`
- `backend`: FastAPI on port `8000`
- `db`: PostgreSQL
- `redis`: Redis

This keeps the current architecture intact and avoids extra platform-specific setup.

## 1. Prepare a Server

Use any Ubuntu/Debian VM with:

- Docker
- Docker Compose plugin
- Ports `80` and `8000` open

Clone the repo onto the server:

```bash
git clone <your-repo-url>
cd churner
```

## 2. Set Environment Variables

Export these before starting:

```bash
export POSTGRES_PASSWORD='change-this'
export VITE_API_URL='http://YOUR_SERVER_IP:8000'
export ANTHROPIC_API_KEY='sk-ant-...'   # optional
```

If you are using a domain and reverse proxy later, set `VITE_API_URL` to your backend public URL instead.

## 3. Start the Stack

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Then verify:

```bash
curl http://YOUR_SERVER_IP/ 
curl http://YOUR_SERVER_IP:8000/health
```

## 4. App URLs

- Frontend: `http://YOUR_SERVER_IP`
- API: `http://YOUR_SERVER_IP:8000`
- API docs: `http://YOUR_SERVER_IP:8000/docs`

## Notes

- First boot can take around 60-90 seconds because the app seeds data and trains models.
- The production backend does not run `--reload`.
- The production frontend is a compiled static build, not the Vite dev server.
- PostgreSQL and Redis both persist data in Docker volumes.

## Updating After Changes

From the repo on the server:

```bash
git pull
docker compose -f docker-compose.prod.yml up --build -d
```

## Recommended Next Step

For a cleaner public deployment, put Nginx, Caddy, or a cloud load balancer in front of the app and expose:

- `https://your-domain.com` -> frontend
- `https://api.your-domain.com` -> backend

If you want, the next step I can do is wire this repo for one specific target:

- Render
- Railway
- Vercel + backend host
- A single VPS with domain + HTTPS
