"""Verify the icpp-binaryen version pins across the downstream repos.

Downstream coupling activates per the integration phases (HANDOVER.md §4):
- Phase 1: llama_cpp_canister requirements.txt (hard pin ==) and
  docker/docker-compose.yml (icpp_binaryen anchor).
- Phase 2: icpp-pro pyproject.toml dependency.

Until a phase has landed, its missing pin is reported as informational, not
as a failure.

Run from the repo root: python -m scripts.check_downstream_pins
"""

import re
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent.resolve()
REPOS_PATH = ROOT_PATH.parent

VERSION_PY = ROOT_PATH / "src/icpp_binaryen/version.py"
LLAMA_REQUIREMENTS = REPOS_PATH / "llama_cpp_canister/requirements.txt"
LLAMA_COMPOSE = REPOS_PATH / "llama_cpp_canister/docker/docker-compose.yml"
ICPP_PRO_PYPROJECT = REPOS_PATH / "icpp-pro/pyproject.toml"


def extract(path: Path, pattern: str) -> str | None:
    """First regex group in path's content, or None."""
    if not path.exists():
        return None
    match = re.search(pattern, path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def main() -> int:
    """Check all downstream pins; 0 = no mismatches."""
    failures: list[str] = []

    our_version = extract(VERSION_PY, r'__version__ = "([\d\.]+)"')
    if our_version is None:
        print(f"ERROR: cannot read version from {VERSION_PY}")
        return 1
    print(f"icpp-binaryen version: {our_version}")

    def check(label: str, actual: str | None) -> None:
        if actual is None:
            print(f"ℹ️  {label}: no icpp-binaryen pin yet (phase not landed)")
        elif actual == our_version:
            print(f"✅ {label}: {actual}")
        else:
            failures.append(f"{label}: expected {our_version}, found {actual}")

    check(
        "llama_cpp_canister requirements.txt",
        extract(LLAMA_REQUIREMENTS, r"icpp-binaryen==([\d\.]+)"),
    )
    check(
        "llama_cpp_canister docker-compose.yml",
        extract(LLAMA_COMPOSE, r'icpp_binaryen: &icpp_binaryen "([\d\.]+)"'),
    )
    check(
        "icpp-pro pyproject.toml",
        extract(ICPP_PRO_PYPROJECT, r'"icpp-binaryen[>=]=([\d\.]+)"'),
    )

    if failures:
        print("\n❌ pin mismatches:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
