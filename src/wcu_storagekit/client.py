from __future__ import annotations

from typing import Any, Dict, Tuple
import posixpath

import fsspec
from fsspec.core import url_to_fs

from .config import StorageConfig, load_from_env
from .errors import UnknownProvider, InvalidURI


class StorageClient:
    """Explicit-provider, config-driven wrapper over fsspec."""

    def __init__(self, cfg: StorageConfig):
        self.cfg = cfg
        self._fs_cache: Dict[Tuple[str, Tuple[Tuple[str, Any], ...]], Any] = {}

    @classmethod
    def from_env(cls, env_var: str = 'STORAGEKIT_CONFIG') -> 'StorageClient':
        return cls(load_from_env(env_var=env_var))

    def open(self, uri: str, mode: str = 'rb', **kwargs):
        resolved, opts = self._resolve(uri)
        return fsspec.open(resolved, mode=mode, **opts, **kwargs)

    def upload(self, local_path: str, dest_uri: str, recursive: bool = False) -> None:
        resolved, opts = self._resolve(dest_uri)
        fs, rpath = self._fs_and_path(resolved, opts)
        fs.put(local_path, rpath, recursive=recursive)

    def download(self, src_uri: str, local_path: str, recursive: bool = False) -> None:
        resolved, opts = self._resolve(src_uri)
        fs, rpath = self._fs_and_path(resolved, opts)
        fs.get(rpath, local_path, recursive=recursive)

    def copy(self, src_uri: str, dst_uri: str, recursive: bool = False) -> None:
        src_res, src_opts = self._resolve(src_uri)
        dst_res, dst_opts = self._resolve(dst_uri)

        src_fs, src_path = self._fs_and_path(src_res, src_opts)
        dst_fs, dst_path = self._fs_and_path(dst_res, dst_opts)

        if src_fs is dst_fs and hasattr(src_fs, 'cp'):
            src_fs.cp(src_path, dst_path, recursive=recursive)
            return

        with fsspec.open(src_res, 'rb', **src_opts) as r:
            with fsspec.open(dst_res, 'wb', **dst_opts) as w:
                while True:
                    chunk = r.read(8 * 1024 * 1024)
                    if not chunk:
                        break
                    w.write(chunk)

    def exists(self, uri: str) -> bool:
        resolved, opts = self._resolve(uri)
        fs, path = self._fs_and_path(resolved, opts)
        return fs.exists(path)

    def ls(self, uri: str, detail: bool = False):
        resolved, opts = self._resolve(uri)
        fs, path = self._fs_and_path(resolved, opts)
        return fs.ls(path, detail=detail)

    def glob(self, uri_pattern: str, detail: bool = False):
        resolved, opts = self._resolve(uri_pattern)
        fs, pattern = self._fs_and_path(resolved, opts)
        if hasattr(fs, 'glob'):
            return fs.glob(pattern, detail=detail)
        return fs.find(posixpath.dirname(pattern))

    def info(self, uri: str) -> Dict[str, Any]:
        resolved, opts = self._resolve(uri)
        fs, path = self._fs_and_path(resolved, opts)
        return fs.info(path)

    def rm(self, uri: str, recursive: bool = False) -> None:
        resolved, opts = self._resolve(uri)
        fs, path = self._fs_and_path(resolved, opts)
        fs.rm(path, recursive=recursive)

    def makedirs(self, uri: str, exist_ok: bool = True) -> None:
        resolved, opts = self._resolve(uri)
        fs, path = self._fs_and_path(resolved, opts)
        if hasattr(fs, 'makedirs'):
            fs.makedirs(path, exist_ok=exist_ok)
        else:
            fs.mkdir(path, create_parents=True)

    def _resolve(self, uri: str) -> tuple[str, Dict[str, Any]]:
        if '://' not in uri:
            raise InvalidURI(f"URI must include provider alias (e.g., primary://...): {uri}")

        alias, rel = uri.split('://', 1)
        if alias not in self.cfg.providers:
            raise UnknownProvider(f"Unknown provider alias '{alias}'. Known: {list(self.cfg.providers)}")

        pcfg = self.cfg.providers[alias]
        resolved = self._join(pcfg.base_uri, rel)
        return resolved, dict(pcfg.options)

    def _fs_and_path(self, resolved_uri: str, opts: Dict[str, Any]):
        proto = resolved_uri.split(':', 1)[0]
        opt_key = tuple(sorted(opts.items()))
        cache_key = (proto, opt_key)

        if cache_key in self._fs_cache:
            fs = self._fs_cache[cache_key]
            _, path = url_to_fs(resolved_uri, **opts)
            return fs, path

        fs, path = url_to_fs(resolved_uri, **opts)
        self._fs_cache[cache_key] = fs
        return fs, path

    @staticmethod
    def _join(base_uri: str, relative: str) -> str:
        base = base_uri.rstrip('/')
        rel = relative.lstrip('/')
        if not rel:
            return base

        if '://' in base:
            scheme, rest = base.split('://', 1)
            if '/' in rest:
                authority, base_path = rest.split('/', 1)
                joined = posixpath.join('/' + base_path, rel).lstrip('/')
                return f"{scheme}://{authority}/{joined}"
            return f"{scheme}://{rest}/{rel}"

        return posixpath.join(base, rel)
