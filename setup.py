"""Packaging for icpp-binaryen.

Metadata lives in pyproject.toml; this file supplies the dynamic version and
the platform-specific wheel tagging.
"""

import pathlib
import sys

from setuptools import find_packages, setup

try:
    from setuptools.command.bdist_wheel import bdist_wheel
except ImportError:  # setuptools < 70.1
    from wheel.bdist_wheel import bdist_wheel  # type: ignore[no-redef]

here = pathlib.Path(__file__).parent.resolve()
# pylint: disable = wrong-import-position, no-member
sys.path.append(str(here / "src/icpp_binaryen"))
import version  # type: ignore


class BdistWheelPlatform(bdist_wheel):  # type: ignore[misc]
    """Tag the wheel py3-none-<platform>.

    ABI-mode cffi needs no compiled extension module, so one wheel per
    platform covers every supported Python version; the bundled libbinaryen
    makes the wheel platform specific.
    """

    def finalize_options(self) -> None:
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self) -> tuple[str, str, str]:
        _, _, plat = super().get_tag()
        return "py3", "none", plat


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
    cmdclass={"bdist_wheel": BdistWheelPlatform},
)
