"""The offline evaluations in backend/evals/ must never become a runtime dependency.

evals/ is excluded from the Docker image (.dockerignore), so if anything under app/
imported it, the API would work in development and fail to start in production.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_no_app_module_imports_evals() -> None:
    pattern = re.compile(r"^\s*(from\s+evals\b|import\s+evals\b)", re.MULTILINE)
    offenders = [
        str(path.relative_to(BACKEND))
        for path in (BACKEND / "app").rglob("*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_starting_the_app_loads_no_evaluation_code() -> None:
    # A fresh interpreter, so modules the test suite itself imported do not count.
    loaded = subprocess.run(
        [sys.executable, "-c", "import sys, app.main; print(sorted(m for m in sys.modules if m.split('.')[0] == 'evals'))"],
        capture_output=True,
        check=True,
        cwd=BACKEND,
        text=True,
    ).stdout.strip()
    assert loaded == "[]"
