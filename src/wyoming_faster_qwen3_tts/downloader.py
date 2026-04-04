from __future__ import annotations

import hashlib
import inspect
import logging
import shutil
import tempfile
from contextlib import suppress
from pathlib import Path

from .constants import ModelProfile

_LOGGER = logging.getLogger(__name__)


def _import_snapshot_download():
    try:
        from modelscope.hub.snapshot_download import snapshot_download

        return snapshot_download
    except ImportError:
        from modelscope import snapshot_download

        return snapshot_download


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _remove_path(path: Path) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)
    return True


def _cleanup_stale_temp_artifacts(parent_dir: Path, model_name: str) -> list[str]:
    removed: list[str] = []
    patterns = (
        "modelscope-*",
        f"{model_name}.tmp*",
        f"{model_name}.partial*",
        f"{model_name}.incomplete*",
        f"{model_name}.download*",
    )
    for pattern in patterns:
        for path in sorted(parent_dir.glob(pattern)):
            if _remove_path(path):
                removed.append(path.name)
    return removed


def _cleanup_empty_dirs(root_dir: Path, keep_paths: set[Path] | None = None) -> list[str]:
    keep_paths = keep_paths or set()
    removed: list[str] = []
    for path in sorted((item for item in root_dir.rglob("*") if item.is_dir()), reverse=True):
        relative_path = path.relative_to(root_dir)
        if relative_path in keep_paths:
            continue
        with suppress(OSError):
            path.rmdir()
            removed.append(str(relative_path))
    return removed


def _required_relative_paths(required_files: tuple[str, ...]) -> set[Path]:
    return {Path(relative_path) for relative_path in required_files}


def _prune_unused_files(model_dir: Path, required_files: tuple[str, ...]) -> list[str]:
    required_paths = _required_relative_paths(required_files)
    required_dirs = {Path(".")}
    for required_path in required_paths:
        required_dirs.update(required_path.parents)

    removed: list[str] = []
    for file_path in sorted((path for path in model_dir.rglob("*") if path.is_file()), reverse=True):
        relative_path = file_path.relative_to(model_dir)
        if relative_path not in required_paths:
            file_path.unlink()
            removed.append(str(relative_path))

    for dir_path in sorted((path for path in model_dir.rglob("*") if path.is_dir()), reverse=True):
        relative_path = dir_path.relative_to(model_dir)
        if relative_path not in required_dirs:
            shutil.rmtree(dir_path, ignore_errors=True)
            removed.append(f"{relative_path}/")

    return removed


class ModelDownloadError(RuntimeError):
    pass


class ModelIntegrityError(RuntimeError):
    pass


def verify_model_directory(
    model_dir: Path,
    required_files: tuple[str, ...],
    expected_sha256: dict[str, str],
) -> None:
    missing = [relative_path for relative_path in required_files if not (model_dir / relative_path).exists()]
    if missing:
        raise ModelIntegrityError(f"Model directory is missing required files: {missing}")

    for relative_path, expected_sha in expected_sha256.items():
        file_path = model_dir / relative_path
        actual_sha = _file_sha256(file_path)
        if actual_sha != expected_sha:
            raise ModelIntegrityError(
                f"Checksum mismatch for {relative_path}: expected {expected_sha}, got {actual_sha}"
            )


def ensure_model_downloaded(model_dir: Path, model_profile: ModelProfile) -> Path:
    model_name = model_profile.model_name
    model_revision = model_profile.model_revision
    required_files = model_profile.required_files
    expected_sha256 = model_profile.expected_sha256
    prune_unused = model_profile.prune_unused

    model_dir.parent.mkdir(parents=True, exist_ok=True)
    removed_artifacts = _cleanup_stale_temp_artifacts(model_dir.parent, model_dir.name)
    if removed_artifacts:
        _LOGGER.info("Removed %d stale download artifacts from %s", len(removed_artifacts), model_dir.parent)

    if model_dir.exists():
        if not model_dir.is_dir():
            _remove_path(model_dir)
            _LOGGER.warning("Removed non-directory model path: %s", model_dir)
        else:
            try:
                verify_model_directory(model_dir, required_files, expected_sha256)
                if prune_unused:
                    removed = _prune_unused_files(model_dir, required_files)
                    if removed:
                        _LOGGER.info("Removed %d unused model files from %s", len(removed), model_dir)
                removed_dirs = _cleanup_empty_dirs(model_dir, keep_paths={Path("speech_tokenizer")})
                if removed_dirs:
                    _LOGGER.info("Removed %d empty model directories from %s", len(removed_dirs), model_dir)
                _LOGGER.info("Using existing validated model directory: %s", model_dir)
                return model_dir
            except ModelIntegrityError as err:
                _LOGGER.warning("Removing invalid model directory %s: %s", model_dir, err)
                shutil.rmtree(model_dir, ignore_errors=True)

    snapshot_download = _import_snapshot_download()
    signature = inspect.signature(snapshot_download)
    temp_parent = Path(tempfile.mkdtemp(prefix="modelscope-", dir=str(model_dir.parent)))
    temp_dir = temp_parent / model_dir.name
    _LOGGER.info("Downloading %s@%s into %s", model_name, model_revision, model_dir)

    try:
        kwargs = {}
        if "model_id" in signature.parameters:
            kwargs["model_id"] = model_name
        if "revision" in signature.parameters:
            kwargs["revision"] = model_revision
        if "local_dir" in signature.parameters:
            kwargs["local_dir"] = str(temp_dir)
        elif "cache_dir" in signature.parameters:
            kwargs["cache_dir"] = str(temp_parent)
        if required_files:
            if "allow_patterns" in signature.parameters:
                kwargs["allow_patterns"] = list(required_files)
            elif "allow_file_pattern" in signature.parameters:
                kwargs["allow_file_pattern"] = list(required_files)

        downloaded = snapshot_download(**kwargs) if kwargs else snapshot_download(model_name)
        downloaded_path = Path(downloaded).resolve()
        if downloaded_path != temp_dir.resolve():
            _copy_tree(downloaded_path, temp_dir)

        verify_model_directory(temp_dir, required_files, expected_sha256)
        if prune_unused:
            removed = _prune_unused_files(temp_dir, required_files)
            if removed:
                _LOGGER.info("Removed %d unused model files from downloaded snapshot", len(removed))
        removed_dirs = _cleanup_empty_dirs(temp_dir, keep_paths={Path("speech_tokenizer")})
        if removed_dirs:
            _LOGGER.info("Removed %d empty model directories from downloaded snapshot", len(removed_dirs))
        temp_dir.rename(model_dir)
        temp_parent.rmdir()
        _cleanup_empty_dirs(model_dir.parent, keep_paths={Path(model_dir.name), Path(".")})
        _LOGGER.info("Model download and validation completed: %s", model_dir)
        return model_dir
    except Exception as err:
        shutil.rmtree(temp_parent, ignore_errors=True)
        if model_dir.exists():
            shutil.rmtree(model_dir, ignore_errors=True)
        if isinstance(err, (ModelDownloadError, ModelIntegrityError)):
            raise
        raise ModelDownloadError(f"Failed to download model from ModelScope: {err}") from err
