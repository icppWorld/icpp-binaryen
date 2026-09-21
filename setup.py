"""Packaging for icpp-binaryen.

Metadata lives in pyproject.toml; this file supplies the dynamic version and
the platform-specific wheel tagging.
"""

import pathlib
import platform
import sys

from setuptools import find_packages, setup
from setuptools.dist import Distribution

try:
    from setuptools.command.bdist_wheel import bdist_wheel
except ImportError:  # setuptools < 70.1
    from wheel.bdist_wheel import bdist_wheel  # type: ignore[no-redef]

here = pathlib.Path(__file__).parent.resolve()
# pylint: disable = wrong-import-position, no-member
sys.path.append(str(here / "src/icpp_binaryen"))
import version  # type: ignore


class BinaryDistribution(Distribution):  # type: ignore[misc]
    """Force a platlib wheel (Root-Is-Purelib: false).

    The bundled libbinaryen makes the wheel platform specific even though
    there is no compiled extension module. Claiming ext_modules is the
    setuptools-version-proof way to get a platlib wheel; auditwheel refuses
    to analyze a purelib wheel that carries a shared library.
    """

    def has_ext_modules(self) -> bool:
        return True


class BdistWheelPlatform(bdist_wheel):  # type: ignore[misc]
    """Tag the wheel py3-none-<platform>.

    ABI-mode cffi needs no compiled extension module, so one wheel per
    platform covers every supported Python version >= 3.11.
    """

    def get_tag(self) -> tuple[str, str, str]:
        _, _, plat = super().get_tag()
        return "py3", "none", _fix_macos_arch(plat)


def _fix_macos_arch(plat: str) -> str:
    """Replace the arch of a macOS platform tag with the bundled dylib's arch.

    `bdist_wheel` derives the tag from the *interpreter's* build. The CPython
    on GitHub's macOS runners is universal2, so it tags every macOS wheel
    `..._universal2` -- but `scripts/get_binaryen.py` downloads the tarball for
    the *runner's* architecture, so the bundled libbinaryen is single-arch.

    That mismatch is not cosmetic: it makes the Intel and arm64 wheels
    indistinguishable to pip, which then resolves on the macOS version alone
    and hands an arm64 dylib to an Intel mac (seen in icpp-pro CI, 2026-09-21):

        incompatible architecture (have 'arm64', need 'x86_64')

    The tag must describe the payload, not the interpreter.
    """
    if not plat.startswith("macosx_"):
        return plat
    # macosx_<major>_<minor>_<arch> - keep the deployment target, fix the arch.
    prefix, _, _ = plat.rpartition("_")
    return f"{prefix}_{platform.machine()}"


setup(
    version=version.__version__,
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={
        "icpp_binaryen": [
            "lib/libbinaryen.dylib",
            "lib/libbinaryen.so",
            "lib/version.txt",
            "py.typed",
        ]
    },
    distclass=BinaryDistribution,
    cmdclass={"bdist_wheel": BdistWheelPlatform},
)
