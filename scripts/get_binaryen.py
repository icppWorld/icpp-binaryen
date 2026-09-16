"""Fetch the official Binaryen shared library into src/icpp_binaryen/lib/.

Downloads the official release tarball for this platform, verifies its
published .sha256, and:
- macOS: ships lib/libbinaryen.dylib as-is.
- Linux: relinks the official static lib/libbinaryen.a into libbinaryen.so
  (the exact technique proven in llama_cpp_canister's Dockerfile.base), so
  the official Binaryen object code is kept byte-for-byte.

The Binaryen version is the major component of icpp_binaryen.version.

Run from the repo root: python -m scripts.get_binaryen  (or `make get-binaryen`)
"""

import hashlib
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent.resolve()
LIB_DIR = ROOT_PATH / "src/icpp_binaryen/lib"
VERSION_PY = ROOT_PATH / "src/icpp_binaryen/version.py"

RELEASE_URL = "https://github.com/WebAssembly/binaryen/releases/download"


def binaryen_version() -> str:
    """The bundled Binaryen version = major of __version__ (see version.py)."""
    match = re.search(r'__version__ = "(\d+)\.', VERSION_PY.read_text())
    if match is None:
        sys.exit(f"ERROR: cannot parse __version__ from {VERSION_PY}")
    return match.group(1)


def tarball_name(version: str) -> str:
    """Official release tarball name for this platform."""
    system = platform.system()
    machine = platform.machine()
    if system == "Darwin":
        arch = "arm64" if machine == "arm64" else "x86_64"
        return f"binaryen-version_{version}-{arch}-macos.tar.gz"
    if system == "Linux" and machine == "x86_64":
        return f"binaryen-version_{version}-x86_64-linux.tar.gz"
    sys.exit(f"ERROR: unsupported platform {system}/{machine}")


def download(url: str, target: Path) -> None:
    """Download url to target."""
    print(f"Downloading {url}")
    with urllib.request.urlopen(url) as response:  # nosec - fixed https URL
        target.write_bytes(response.read())


def verify_sha256(tarball: Path, sha_file: Path) -> None:
    """Verify the tarball against its published .sha256 file."""
    published = sha_file.read_text().split()[0].strip()
    actual = hashlib.sha256(tarball.read_bytes()).hexdigest()
    if actual != published:
        sys.exit(
            f"ERROR: sha256 mismatch for {tarball.name}\n"
            f"  published: {published}\n"
            f"  actual   : {actual}"
        )
    print(f"sha256 verified: {actual}")


def extract_lib(tarball: Path, version: str, dest_dir: Path) -> None:
    """Extract the shared library (relinking the .a on Linux)."""
    system = platform.system()
    member_name = "libbinaryen.dylib" if system == "Darwin" else "libbinaryen.a"
    member = f"binaryen-version_{version}/lib/{member_name}"
    with tarfile.open(tarball) as tar:
        info = tar.getmember(member)
        info.name = member_name
        tar.extract(info, dest_dir, filter="data")
    print(f"Extracted {member_name}")

    if system == "Linux":
        # Relink the official static archive into a shared object; keeps the
        # official object code byte-for-byte (proven in production at 116).
        subprocess.run(
            [
                "g++",
                "-shared",
                "-o",
                "libbinaryen.so",
                "-Wl,--whole-archive",
                "libbinaryen.a",
                "-Wl,--no-whole-archive",
                "-lstdc++",
                "-lm",
            ],
            cwd=dest_dir,
            check=True,
        )
        (dest_dir / "libbinaryen.a").unlink()
        print("Relinked libbinaryen.a -> libbinaryen.so")


def main() -> int:
    """Fetch, verify, and install the bundled Binaryen library."""
    version = binaryen_version()
    name = tarball_name(version)

    if LIB_DIR.exists():
        shutil.rmtree(LIB_DIR)
    LIB_DIR.mkdir(parents=True)

    with tempfile.TemporaryDirectory() as tmp:
        tarball = Path(tmp) / name
        sha_file = Path(tmp) / f"{name}.sha256"
        download(f"{RELEASE_URL}/version_{version}/{name}", tarball)
        download(f"{RELEASE_URL}/version_{version}/{name}.sha256", sha_file)
        verify_sha256(tarball, sha_file)
        extract_lib(tarball, version, LIB_DIR)

    (LIB_DIR / "version.txt").write_text(version, encoding="utf-8")
    print(f"Done: {LIB_DIR} (Binaryen {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
