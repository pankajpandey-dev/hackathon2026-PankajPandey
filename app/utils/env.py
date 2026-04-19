from __future__ import annotations


def env_float(name: str, default: str) -> float:
    """Read float from env; strip inline `#` comments sometimes present in `.env` files."""
    return float(__import__("os").getenv(name, default).split("#", 1)[0].strip())
