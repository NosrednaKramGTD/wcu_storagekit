from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import os
import re
from pathlib import Path

import yaml

from .errors import ConfigError

_ENV_PATTERN = re.compile(r'\$\{([A-Z0-9_]+)\}')


@dataclass(frozen=True)
class ProviderConfig:
    base_uri: str
    options: Dict[str, Any]


@dataclass(frozen=True)
class StorageConfig:
    providers: Dict[str, ProviderConfig]
    env_substitution: bool = True


def _env_substitute(value: Any) -> Any:
    """Recursively substitute ${VARNAME} inside strings with os.environ values."""
    if isinstance(value, str):
        def repl(m):
            var = m.group(1)
            if var not in os.environ:
                raise ConfigError(f"Missing environment variable for substitution: {var}")
            return os.environ[var]
        return _ENV_PATTERN.sub(repl, value)

    if isinstance(value, dict):
        return {k: _env_substitute(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_env_substitute(v) for v in value]

    return value


def load_from_yaml_path(path: str) -> StorageConfig:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {path}")

    raw = yaml.safe_load(p.read_text()) or {}
    storage = raw.get('storage', {})

    env_sub = bool(storage.get('env_substitution', True))
    if env_sub:
        raw = _env_substitute(raw)
        storage = raw.get('storage', {})

    providers = storage.get('providers', {})
    if not isinstance(providers, dict) or not providers:
        raise ConfigError('Config must define storage.providers with at least one provider')

    parsed: Dict[str, ProviderConfig] = {}
    for name, pcfg in providers.items():
        if 'base_uri' not in pcfg:
            raise ConfigError(f"Provider '{name}' missing base_uri")
        parsed[name] = ProviderConfig(
            base_uri=str(pcfg['base_uri']),
            options=dict(pcfg.get('options', {}) or {}),
        )

    return StorageConfig(providers=parsed, env_substitution=env_sub)


def load_from_env(env_var: str = 'STORAGEKIT_CONFIG') -> StorageConfig:
    path = os.environ.get(env_var)
    if not path:
        raise ConfigError(f"Environment variable '{env_var}' not set")
    return load_from_yaml_path(path)
