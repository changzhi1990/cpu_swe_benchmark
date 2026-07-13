from __future__ import annotations

import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_TEMPLATES_DIR = PROJECT_ROOT / "repo_templates"


def repo_template_path(name: str) -> Path:
    path = REPO_TEMPLATES_DIR / name
    if not path.is_dir():
        raise ValueError(f"Unknown repo template: {name}")
    return path


def copy_repo_template(name: str, destination: Path) -> None:
    source = repo_template_path(name)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git"))
