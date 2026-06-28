# Secret management

## How secrets are loaded

`src/common/secrets.py:get_secret(name)` resolves a secret in this order:

1. `<NAME>_FILE` — path to a file containing the secret value. Point this at
   a file mounted by Docker secrets, Kubernetes secrets, Vault Agent, or AWS
   Secrets Manager's file-sync sidecar. This is the integration point for a
   real secret manager — no code change needed, just mount a file and set
   `<NAME>_FILE=/path/to/it`.
2. `<NAME>` — plain environment variable, sourced from `.env` locally.
3. A default, only for non-sensitive values (hosts, ports, usernames).
   Passwords and tokens have no default and raise `MissingSecretError` if
   neither of the above is set — a hardcoded fallback password in source is
   a real credential for anyone who forgets to configure it.

`.env` is gitignored and must never be committed. `.env.example` documents
every variable with no real values — copy it to `.env` and fill it in.

## Where each secret comes from

| Secret | Source |
|---|---|
| `POSTGRES_PASSWORD`, `CLICKHOUSE_PASSWORD` | Set when standing up the stack; also baked into `docker-compose.yml` as the container's own credential, so they must match. |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | Set when standing up the stack. |
| `DNSE_API_KEY` / `DNSE_API_SECRET` | Issued by DNSE for market data API access. |
| `TELEGRAM_BOT_TOKEN` | From `@BotFather` on Telegram when creating the alert bot. |
| `SMTP_PASSWORD` | App password for the SMTP account used to send alert emails (e.g. a Gmail App Password, not the account password). |
| `AIRFLOW_WEBSERVER_SECRET_KEY`, `SUPERSET_SECRET_KEY` | Generated locally (`openssl rand -hex 32`), used only to sign that app's own sessions. |

## Rotation

- **Telegram bot token**: revoke and regenerate via `@BotFather` -> `/revoke`,
  update `TELEGRAM_BOT_TOKEN`, restart `alert-engine`.
- **SMTP app password**: revoke in the email provider's app-password
  settings, generate a new one, update `SMTP_PASSWORD`, restart
  `alert-engine`.
- **DNSE API key/secret**: rotate via the DNSE developer portal, update
  `DNSE_API_KEY`/`DNSE_API_SECRET`, restart whatever ingestion job uses it.
- **Postgres/ClickHouse passwords**: changing these requires updating both
  the running server (`ALTER USER ... PASSWORD ...` / ClickHouse user XML or
  `ALTER USER`) and every `.env`/`docker-compose.yml` reference, then
  restarting all dependent containers. Do this during a maintenance window —
  it is not hot-reloadable.
- After any rotation, run `uv run python scripts/check_env.py` to confirm the
  new value is actually being picked up (it only prints `set`/`missing`, not
  the value, so it's safe to run anywhere).

## What this is not

This is not a Vault/AWS Secrets Manager integration — there is no running
secret-manager service in this stack. The `_FILE` convention is the seam
that lets one be added later (mount its output, point `<NAME>_FILE` at it)
without touching application code. For a single-developer local lakehouse
project, a real secret-manager service would be infrastructure with no
corresponding operational need; the actual fixed gaps here are (a) no
hardcoded fallback passwords in source, (b) a documented, git-tracked list
of what every secret is and how to rotate it.
