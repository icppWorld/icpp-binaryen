"""Byte-identical parity gate for releases that keep the bundled Binaryen.

Runs fix_globals_limit on a real llama_cpp_canister artifact and compares the
output sha256 against the recorded golden (test/parity/golden-116.json).

How the golden was established (macOS arm64): fix_globals_limit output on
llama_cpp_before_opt.wasm is byte-identical to running the exact same C API
sequence through binaryen.py==0.0.2 (the package icpp-binaryen replaces) on
the same input. First recorded 2026-09-16; re-established 2026-09-21 against
a rebuilt llama artifact, again byte-identical.

NOTE: llama's final build/llama_cpp.wasm is NOT a valid comparison target —
icpp-pro appends metadata custom sections (icp:public candid:service,
cdk:name, ...) AFTER the post_wasm_function hook runs. Byte-identical hook
output still implies an unchanged final wasm hash downstream.

Run from the repo root: python -m scripts.parity_test  (or `make parity-test`)
Pass --write-golden to (re)record the golden after independent verification.
"""

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent.resolve()
GOLDEN_PATH = ROOT_PATH / "test/parity/golden-116.json"
DEFAULT_WASM = ROOT_PATH.parent / "llama_cpp_canister/build/llama_cpp_before_opt.wasm"


def sha256_of(path: Path) -> str:
    """sha256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    """Run the parity gate; 0 = parity OK or skipped."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wasm",
        type=Path,
        default=DEFAULT_WASM,
        help="input wasm (default: sibling llama_cpp_before_opt.wasm)",
    )
    parser.add_argument(
        "--write-golden",
        action="store_true",
        help="record input/output hashes as the new golden",
    )
    args = parser.parse_args()

    if not args.wasm.exists():
        print(f"PARITY SKIPPED: input not found: {args.wasm}")
        print("Build llama_cpp_canister first, or pass --wasm <path>.")
        return 0

    # Import late so --help works without the bundled lib present
    from icpp_binaryen import (  # pylint: disable = import-outside-toplevel
        fix_globals_limit,
    )

    input_sha = sha256_of(args.wasm)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / args.wasm.name.replace("_before_opt", "")
        shutil.copy(args.wasm, work)
        report = fix_globals_limit(work)
        print(report.summary())
        output_sha = sha256_of(work)

    print(f"input  sha256: {input_sha}")
    print(f"output sha256: {output_sha}")

    if args.write_golden:
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_text(
            json.dumps(
                {
                    "input": args.wasm.name,
                    "input_sha256": input_sha,
                    "output_sha256": output_sha,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Golden written: {GOLDEN_PATH}")
        return 0

    if not GOLDEN_PATH.exists():
        print(f"ERROR: no golden recorded yet ({GOLDEN_PATH}).")
        print("Verify parity independently, then rerun with --write-golden.")
        return 1

    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    if input_sha != golden["input_sha256"]:
        print("ERROR: the input wasm differs from the one the golden was")
        print("recorded against (a rebuild changed llama_cpp_before_opt.wasm).")
        print("Re-establish parity, then rerun with --write-golden.")
        return 1
    if output_sha != golden["output_sha256"]:
        print("PARITY FAILED: output bytes changed for the same input.")
        print(f"  golden : {golden['output_sha256']}")
        print(f"  actual : {output_sha}")
        return 1

    print("PARITY OK: byte-identical output")
    return 0


if __name__ == "__main__":
    sys.exit(main())
