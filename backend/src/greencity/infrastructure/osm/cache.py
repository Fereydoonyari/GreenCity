"""Disk cache for Overpass JSON responses."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)


class OverpassDiskCache:
    """Simple TTL file cache keyed by query fingerprint."""

    def __init__(self, cache_dir: str | Path, *, ttl_s: int = 86_400) -> None:
        self._dir = Path(cache_dir)
        self._ttl_s = max(0, int(ttl_s))
        if self._ttl_s > 0:
            self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self._ttl_s > 0

    def get(self, query: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        path = self._path_for(query)
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > self._ttl_s:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        _log.info("Overpass cache hit (%s)", path.name)
        return payload

    def set(self, query: str, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        path = self._path_for(query)
        try:
            path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError as exc:
            _log.warning("Overpass cache write failed (%s): %s", path, exc)

    def _path_for(self, query: str) -> Path:
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()[:40]
        return self._dir / f"{digest}.json"
