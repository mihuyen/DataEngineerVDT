from __future__ import annotations

import os
from pathlib import Path


class MissingSecretError(RuntimeError):
    pass


def get_secret(name: str, default: str | None = None, required: bool = False) -> str | None:
    """Resolve a secret by name.

    Lookup order:
    1. ``{name}_FILE`` -- path to a file holding the secret. This is the
       standard convention Docker secrets, Kubernetes secrets, and Vault
       Agent/AWS Secrets Manager file-sync sidecars all use, so pointing this
       at a mounted file is how a real secret manager plugs in later without
       any code change here.
    2. ``{name}`` -- plain environment variable, the local-dev path (from
       ``.env``, never committed).
    3. ``default`` if given, else raise when ``required``.

    Hardcoding a fallback password in source (e.g. ``getenv("X", "admin")``)
    means that password is the de facto credential for anyone who never sets
    the env var, including in a misconfigured production deploy. Call sites
    for real credentials should pass ``required=True`` and no default.
    """
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        value = Path(file_path).read_text(encoding="utf-8").strip()
        if value:
            return value

    value = os.getenv(name)
    if value:
        return value

    if default is not None:
        return default

    if required:
        raise MissingSecretError(
            f"Missing required secret '{name}'. Set the {name} environment variable "
            f"(or {name}_FILE to point at a mounted secret file)."
        )

    return None
