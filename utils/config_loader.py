"""config_loader.py — environment-aware configuration loader.

Loading order (later values win):
  1. config/base.yaml            — device, browser, shared test defaults
  2. config/environments/<env>.yaml — env-specific URLs, accounts, timeouts
  3. config/.env.<env>           — actual secret values (gitignored)
  4. OS environment variables    — CI/CD injected secrets always win

Placeholder syntax in YAML values:  ${MY_VAR}
  → replaced with the matching environment variable at load time.
  → if the variable is missing the placeholder is left as-is and a
    warning is printed so CI logs surface missing secrets early.
"""

import os
import re
import warnings
from typing import Any

import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PLACEHOLDER = re.compile(r"\$\{(\w+)\}")

SUPPORTED_ENVS = ("staging", "production")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(env: str) -> dict:
    """Return a fully-resolved config dict for *env*."""
    if env not in SUPPORTED_ENVS:
        raise ValueError(
            f"Unknown environment '{env}'. Supported: {SUPPORTED_ENVS}"
        )

    base = _load_yaml(_path("config", "base.yaml"))
    env_cfg = _load_yaml(_path("config", "environments", f"{env}.yaml"))

    # Inject .env.<env> file before substitution so its values are available
    _load_dotenv(_path("config", f".env.{env}"))

    merged = _deep_merge(base, env_cfg)
    return _substitute_env_vars(merged)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _path(*parts: str) -> str:
    return os.path.join(_ROOT, *parts)


def _load_yaml(filepath: str) -> dict:
    with open(filepath, "r") as fh:
        try:
            return yaml.safe_load(fh) or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML config '{filepath}': {e}") from e


def _load_dotenv(filepath: str) -> None:
    """Parse a .env file and populate os.environ (existing vars take priority)."""
    if not os.path.exists(filepath):
        return
    with open(filepath, "r") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            # Don't override variables already in the environment (CI wins)
            os.environ.setdefault(key.strip(), value.strip())


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*; override wins on conflict."""
    result = base.copy()
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _substitute_env_vars(obj: Any) -> Any:
    """Recursively replace ${VAR} placeholders with their env-var values."""
    if isinstance(obj, str):
        def _replace(match: re.Match) -> str:
            var = match.group(1)
            value = os.environ.get(var)
            if value is None:
                warnings.warn(
                    f"[config_loader] Environment variable '{var}' is not set. "
                    f"The placeholder ${{'{var}'}} will remain unresolved.",
                    stacklevel=2,
                )
                return match.group(0)   # leave placeholder intact
            return value

        return _PLACEHOLDER.sub(_replace, obj)

    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]

    return obj
