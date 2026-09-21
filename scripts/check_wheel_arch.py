"""Verify a built wheel's platform tag matches the bundled library's arch.

The wheel carries a prebuilt libbinaryen, so its filename is a promise about
what is inside it. When the two disagree, pip cannot tell the macOS wheels
apart and installs the wrong one - which is how a `universal2`-tagged,
arm64-only wheel reached Intel macs in 116.0.0.

Run after `make pypi-build`, before anything is published.
"""

import pathlib
import re
import sys
import zipfile

# Mach-O / ELF machine names as `file`-style strings map onto wheel tag archs.
MACHO_ARCH = re.compile(rb"^(?:\xcf\xfa\xed\xfe|\xce\xfa\xed\xfe)")
LIB_NAMES = ("lib/libbinaryen.dylib", "lib/libbinaryen.so")

# Mach-O cputype (little endian, offset 4 of the header) -> wheel tag arch.
CPUTYPE = {0x01000007: "x86_64", 0x0100000C: "arm64"}
# ELF e_machine (offset 18) -> wheel tag arch.
E_MACHINE = {0x3E: "x86_64", 0xB7: "aarch64"}


def lib_arch(blob: bytes) -> str:
    """Architecture of a single-arch Mach-O or ELF shared library."""
    if blob[:4] in (b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
        return "universal2"  # a real fat binary
    if MACHO_ARCH.match(blob):
        cputype = int.from_bytes(blob[4:8], "little")
        return CPUTYPE.get(cputype, f"mach-o:0x{cputype:x}")
    if blob[:4] == b"\x7fELF":
        machine = int.from_bytes(blob[18:20], "little")
        return E_MACHINE.get(machine, f"elf:0x{machine:x}")
    return "unknown"


def check(wheel: pathlib.Path) -> list[str]:
    """Return a list of problems found in one wheel (empty means good)."""
    tag = wheel.stem.split("-")[-1]
    problems = []
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
        libs = [n for n in names if n.endswith(LIB_NAMES)]
        if not libs:
            return [f"{wheel.name}: bundles no libbinaryen"]
        for name in libs:
            arch = lib_arch(zf.read(name))
            if not tag.endswith(arch):
                problems.append(f"{wheel.name}: tag says '{tag}' but {name} is {arch}")
            else:
                print(f"OK  {wheel.name}: tag '{tag}' matches {name} ({arch})")
    return problems


def main() -> None:
    """Check every wheel in dist/."""
    wheels = sorted(pathlib.Path("dist").glob("*.whl"))
    if not wheels:
        sys.exit("ERROR: no wheels in dist/ - run `make pypi-build` first")
    problems = [p for w in wheels for p in check(w)]
    if problems:
        print("\nERROR: wheel tag does not describe the bundled library:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"\n{len(wheels)} wheel(s) correctly tagged")


if __name__ == "__main__":
    main()
