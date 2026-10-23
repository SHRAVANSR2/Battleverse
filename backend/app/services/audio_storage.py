"""Safe on-disk storage for generated audio.

* keys are opaque and generated server-side (``YYYY/MM/<uuid4>.wav``);
* all keys use forward slashes and are resolved under the audio root;
* ``Path.is_relative_to`` rejects traversal before any file operation;
* writes are atomic (temp file in the same directory + ``os.replace``).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.errors import AudioFileMissingError, TTSSynthesisError


class AudioStorage:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()

    def ensure_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, storage_key: str) -> Path:
        """Resolve a stored key to an absolute path, refusing to escape the root."""
        if not storage_key or "\\" in storage_key and ".." in storage_key:
            raise AudioFileMissingError()
        candidate = (self.root / storage_key).resolve()
        if not candidate.is_relative_to(self.root):
            raise AudioFileMissingError()
        return candidate

    def new_key(self, extension: str = "wav") -> str:
        now = datetime.now(timezone.utc)
        token = uuid.uuid4().hex
        return f"{now:%Y}/{now:%m}/{token}.{extension}"

    def write(self, data: bytes, extension: str = "wav") -> tuple[str, int]:
        if not data:
            raise TTSSynthesisError("The speech engine produced an empty file.")
        self.ensure_root()
        key = self.new_key(extension)
        target = self.resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f".{target.name}.tmp")
        try:
            with open(tmp, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, target)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise TTSSynthesisError("We could not save the audio file.") from exc
        return key, len(data)

    def exists(self, storage_key: str) -> bool:
        try:
            path = self.resolve(storage_key)
        except Exception:
            return False
        return path.is_file()

    def size(self, storage_key: str) -> int:
        path = self.resolve(storage_key)
        if not path.is_file():
            raise AudioFileMissingError()
        return path.stat().st_size