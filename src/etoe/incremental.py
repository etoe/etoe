"""Incremental cache for generated ÆToE visualization artifacts.

The sidecar stores content hashes as well as filesystem timestamps.  The hashes
are authoritative: a file whose contents change while its mtime is restored
still invalidates the generated image.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tomllib
from typing import Any, Iterable, Mapping


MANIFEST_SCHEMA = "etoe.generated-image-manifest.v1"
_IMAGE_FORMATS = frozenset({"png", "svg", "pdf", "ps"})


def is_image_format(file_format: str) -> bool:
    """Return whether *file_format* is an image/document render, not source DOT."""
    return file_format.casefold().lstrip(".") in _IMAGE_FORMATS


def manifest_path(output_path: Path) -> Path:
    """Return the adjacent TOML manifest path (``image.png.toml``)."""
    return Path(f"{output_path}.toml")


def _display_path(path: Path) -> str:
    """Prefer portable paths relative to the current working directory."""
    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_dependencies(
    dependencies: Iterable[tuple[Path, str]],
) -> list[dict[str, Any]]:
    """Capture deterministic file metadata for dependency ``(path, role)`` pairs."""
    unique: dict[str, tuple[Path, str]] = {}
    for raw_path, role in dependencies:
        path = Path(raw_path).expanduser().resolve()
        key = str(path)
        # The first role is stable for a given collection order. A dependency
        # normally has exactly one role; de-duplication avoids repeated hashes.
        unique.setdefault(key, (path, str(role)))

    result: list[dict[str, Any]] = []
    for _key, (path, role) in sorted(unique.items()):
        try:
            stat = path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds")
            record: dict[str, Any] = {
                "path": _display_path(path),
                "role": role,
                "exists": True,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "modified_utc": modified,
                "sha256": _hash_file(path),
            }
        except FileNotFoundError:
            # Normally missing paths are omitted by the collector. Keeping this
            # branch makes a race during generation invalidate the cache safely.
            record = {
                "path": _display_path(path),
                "role": role,
                "exists": False,
                "size": 0,
                "mtime_ns": 0,
                "modified_utc": "",
                "sha256": "",
            }
        result.append(record)
    return result


def _context_json(context: Mapping[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _quoted(value: str) -> str:
    # JSON basic strings use escaping compatible with TOML basic strings.
    return json.dumps(value, ensure_ascii=False)


def _serialize_manifest(
    *,
    output_path: Path,
    context: Mapping[str, Any],
    dependencies: list[dict[str, Any]],
    output_sha256: str,
) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        f"schema = {_quoted(MANIFEST_SCHEMA)}",
        f"generated_at = {_quoted(generated_at)}",
        f"output = {_quoted(_display_path(output_path))}",
        f"output_sha256 = {_quoted(output_sha256)}",
        f"context_json = {_quoted(_context_json(context))}",
        "",
    ]
    for dependency in dependencies:
        lines.extend([
            "[[dependencies]]",
            f"path = {_quoted(str(dependency['path']))}",
            f"role = {_quoted(str(dependency['role']))}",
            f"exists = {'true' if dependency['exists'] else 'false'}",
            f"size = {int(dependency['size'])}",
            f"mtime_ns = {int(dependency['mtime_ns'])}",
            f"modified_utc = {_quoted(str(dependency['modified_utc']))}",
            f"sha256 = {_quoted(str(dependency['sha256']))}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def is_cache_current(
    output_path: Path,
    *,
    context: Mapping[str, Any],
    dependencies: Iterable[tuple[Path, str]],
) -> bool:
    """Check image and TOML sidecar against current context and input contents."""
    output_path = Path(output_path)
    companion = manifest_path(output_path)
    if not output_path.is_file() or not companion.is_file():
        return False
    try:
        manifest = tomllib.loads(companion.read_text(encoding="utf-8"))
        if manifest.get("schema") != MANIFEST_SCHEMA:
            return False
        if manifest.get("context_json") != _context_json(context):
            return False
        if manifest.get("output") != _display_path(output_path):
            return False
        if manifest.get("output_sha256") != _hash_file(output_path):
            return False
        expected = snapshot_dependencies(dependencies)
        stored = manifest.get("dependencies", [])
        return stored == expected
    except (OSError, ValueError, TypeError, tomllib.TOMLDecodeError):
        # A stale, hand-edited or malformed cache manifest must never prevent
        # the artifact from being regenerated.
        return False


def write_manifest(
    output_path: Path,
    *,
    context: Mapping[str, Any],
    dependencies: Iterable[tuple[Path, str]],
) -> Path | None:
    """Write a TOML sidecar after a successful render; return its path."""
    output_path = Path(output_path)
    if not output_path.is_file():
        # Allows integrations/tests that replace the renderer with a recorder
        # to preserve the writer's historical return behavior without creating
        # a manifest for an artifact that was never actually written.
        return None
    dependency_snapshot = snapshot_dependencies(dependencies)
    text = _serialize_manifest(
        output_path=output_path,
        context=context,
        dependencies=dependency_snapshot,
        output_sha256=_hash_file(output_path),
    )
    companion = manifest_path(output_path)
    companion.parent.mkdir(parents=True, exist_ok=True)
    temporary = companion.with_name(f".{companion.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(companion)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return companion


__all__ = [
    "MANIFEST_SCHEMA",
    "is_image_format",
    "is_cache_current",
    "manifest_path",
    "snapshot_dependencies",
    "write_manifest",
]
