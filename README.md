# Uply

A simple web app to check if your websites and hosts are up.

## Requirements

- Python 3.11+
- Linux (for ICMP ping support)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ICMP ping permissions

Ping checks require raw socket access. Instead of running the app as root
(which causes file ownership issues with the SQLite database), grant the
capability to the venv Python binary:

```bash
sudo setcap cap_net_raw+ep $(readlink -f venv/bin/python)
```

## Running

```bash
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive docs at `/docs`.

## Configuration

Settings are loaded from environment variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./uply.db` | Database connection string |
| `CHECK_INTERVAL_SECONDS` | `60` | How often monitors are checked |
| `DEFAULT_TIMEOUT_SECONDS` | `10` | Timeout for HTTP/ping checks |
| `DATA_RETENTION_DAYS` | `30` | Auto-delete checks older than this |

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/api/monitors/` | List all monitors |
| `POST` | `/api/monitors/` | Create a monitor |
| `GET` | `/api/monitors/{id}` | Get a monitor |
| `DELETE` | `/api/monitors/{id}` | Delete a monitor |
| `GET` | `/api/monitors/{id}/checks` | Check history |
| `GET` | `/api/monitors/{id}/stats` | Uptime stats |
| `GET` | `/api/monitors/{id}/stats/uptime-chart` | Uptime chart data |
| `GET` | `/api/dashboard/summary` | Dashboard summary |
