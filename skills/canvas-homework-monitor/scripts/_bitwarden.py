"""Helpers for pulling credentials from a self-hosted Bitwarden vault via the `bw` CLI.

Usage pattern:

    from _bitwarden import get_login

    creds = get_login("DCDS - Cora")
    print(creds.username, creds.password)

Login + unlock state is established automatically by sourcing
``~/.config/bitwarden-cli/env.sh`` (which must export ``BW_EMAIL``, ``BW_PASSWORD``,
and optionally ``BW_CLIENTID`` / ``BW_CLIENTSECRET``). The helper caches an
unlocked ``BW_SESSION`` for the current process.

This is deliberately separate from the Canvas script so any future skill that
needs Bitwarden creds can ``from _bitwarden import get_login``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ENV_FILE = Path.home() / ".config" / "bitwarden-cli" / "env.sh"


class BitwardenError(RuntimeError):
    pass


@dataclass(frozen=True)
class BwLogin:
    name: str
    username: str | None
    password: str | None
    uris: tuple[str, ...]
    item_id: str
    raw: dict[str, Any]


def _bw_path() -> str:
    path = shutil.which("bw")
    if not path:
        raise BitwardenError(
            "The `bw` CLI is not on PATH. Install with `npm install -g @bitwarden/cli` "
            "and ensure ~/.npm-global/bin is on PATH."
        )
    return path


def _load_env_file(env_file: Path) -> dict[str, str]:
    """Parse a simple ``export KEY='VALUE'`` env file without invoking a shell."""
    if not env_file.exists():
        return {}
    out: dict[str, str] = {}
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def _ensure_logged_in(env: dict[str, str]) -> None:
    bw = _bw_path()
    status_proc = subprocess.run(
        [bw, "status"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        status = json.loads(status_proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise BitwardenError(
            f"Could not parse `bw status` output: {status_proc.stdout!r} / {status_proc.stderr!r}"
        ) from exc

    if status.get("status") in ("locked", "unlocked"):
        return

    email = env.get("BW_EMAIL")
    password = env.get("BW_PASSWORD")
    if not email or not password:
        raise BitwardenError(
            "Need BW_EMAIL and BW_PASSWORD in the bitwarden-cli env file to log in."
        )
    login_proc = subprocess.run(
        [bw, "login", email, password],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if login_proc.returncode != 0:
        raise BitwardenError(
            f"`bw login` failed (exit {login_proc.returncode}): "
            f"{login_proc.stdout.strip() or login_proc.stderr.strip()}"
        )


def _unlock(env: dict[str, str]) -> str:
    bw = _bw_path()
    if "BW_PASSWORD" not in env:
        raise BitwardenError("Need BW_PASSWORD in the bitwarden-cli env file to unlock.")
    proc = subprocess.run(
        [bw, "unlock", "--passwordenv", "BW_PASSWORD", "--raw"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    session = (proc.stdout or "").strip()
    if not session:
        raise BitwardenError(
            f"`bw unlock` did not return a session token "
            f"(exit {proc.returncode}, stderr={proc.stderr.strip()!r})."
        )
    return session


_session_cache: dict[str, str] = {}


def _get_session(env_file: Path = DEFAULT_ENV_FILE) -> tuple[str, dict[str, str]]:
    cache_key = str(env_file)
    env = os.environ.copy()
    env.update(_load_env_file(env_file))
    cached = _session_cache.get(cache_key)
    if cached:
        env["BW_SESSION"] = cached
        # Verify it is still good.
        bw = _bw_path()
        status_proc = subprocess.run(
            [bw, "status"], env=env, capture_output=True, text=True, check=False
        )
        try:
            status = json.loads(status_proc.stdout.strip().splitlines()[-1])
            if status.get("status") == "unlocked":
                return cached, env
        except (json.JSONDecodeError, IndexError):
            pass

    _ensure_logged_in(env)
    session = _unlock(env)
    env["BW_SESSION"] = session
    _session_cache[cache_key] = session
    return session, env


def sync(env_file: Path = DEFAULT_ENV_FILE) -> None:
    bw = _bw_path()
    _, env = _get_session(env_file)
    proc = subprocess.run(
        [bw, "sync"], env=env, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise BitwardenError(
            f"`bw sync` failed: {proc.stdout.strip() or proc.stderr.strip()}"
        )


def get_login(item_name: str, env_file: Path = DEFAULT_ENV_FILE) -> BwLogin:
    """Look up a Bitwarden login item by name and return its parsed creds."""
    bw = _bw_path()
    _, env = _get_session(env_file)
    proc = subprocess.run(
        [bw, "get", "item", item_name],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise BitwardenError(
            f"`bw get item {item_name!r}` failed: "
            f"{proc.stdout.strip() or proc.stderr.strip()}"
        )
    try:
        item = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise BitwardenError(
            f"`bw get item {item_name!r}` did not return JSON: {proc.stdout!r}"
        ) from exc

    login = item.get("login") or {}
    uris = tuple(
        u.get("uri")
        for u in (login.get("uris") or [])
        if isinstance(u, dict) and u.get("uri")
    )
    return BwLogin(
        name=item.get("name") or item_name,
        username=login.get("username"),
        password=login.get("password"),
        uris=uris,
        item_id=item.get("id") or "",
        raw=item,
    )


__all__ = ["BwLogin", "BitwardenError", "get_login", "sync", "DEFAULT_ENV_FILE"]
