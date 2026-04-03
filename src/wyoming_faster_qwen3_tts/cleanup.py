from __future__ import annotations

import logging
import shutil
from contextlib import suppress
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

_JUNK_DIR_NAMES = {"__pycache__", ".pytest_cache", "build", "dist"}
_AUDIO_OUTPUT_DIRS = ("outputs", "output", "tmp", "temp", "data/outputs", "data/tmp")
_AUDIO_PATTERNS = ("*.wav", "*.mp3", "*.flac", "*.ogg")
_TEMP_FILE_PATTERNS = ("*.tmp", "*.part", "*.partial", "*.download", "*.incomplete")
_BUILD_FILE_PATTERNS = ("*.egg-info",)


def _safe_remove_dir(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    shutil.rmtree(path, ignore_errors=True)
    return True


def _safe_remove_file(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    path.unlink(missing_ok=True)
    return True


def cleanup_build_artifacts(project_root: Path, model_dir: Path) -> tuple[int, int]:
    removed_dirs = 0
    removed_files = 0

    excluded_roots = {
        project_root / ".venv",
        model_dir,
    }

    for path in sorted(project_root.rglob("*")):
        if any(root in path.parents or path == root for root in excluded_roots):
            continue
        if path.is_dir() and path.name in _JUNK_DIR_NAMES:
            if _safe_remove_dir(path):
                removed_dirs += 1
        elif path.is_dir() and any(path.match(pattern) for pattern in _BUILD_FILE_PATTERNS):
            if _safe_remove_dir(path):
                removed_dirs += 1

    return removed_dirs, removed_files


def cleanup_runtime_outputs(project_root: Path) -> tuple[int, int]:
    removed_dirs = 0
    removed_files = 0

    for relative_dir in _AUDIO_OUTPUT_DIRS:
        target_dir = project_root / relative_dir
        if not target_dir.exists() or not target_dir.is_dir():
            continue
        for pattern in _AUDIO_PATTERNS + _TEMP_FILE_PATTERNS:
            for file_path in sorted(target_dir.rglob(pattern)):
                if _safe_remove_file(file_path):
                    removed_files += 1
        for dir_path in sorted((path for path in target_dir.rglob("*") if path.is_dir()), reverse=True):
            with suppress(OSError):
                dir_path.rmdir()
        with suppress(OSError):
            target_dir.rmdir()
            removed_dirs += 1

    return removed_dirs, removed_files


def cleanup_project_junk(project_root: Path, model_dir: Path) -> None:
    build_dirs, build_files = cleanup_build_artifacts(project_root, model_dir)
    runtime_dirs, runtime_files = cleanup_runtime_outputs(project_root)
    removed_dirs = build_dirs + runtime_dirs
    removed_files = build_files + runtime_files

    if removed_dirs or removed_files:
        _LOGGER.info(
            "Removed project junk dirs=%d files=%d under %s",
            removed_dirs,
            removed_files,
            project_root,
        )
