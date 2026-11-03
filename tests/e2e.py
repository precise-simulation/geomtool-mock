#!/usr/bin/env python3
import argparse
import pathlib
import re
import shutil
import subprocess
import sys


def run(exe: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(exe), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print("$", exe.name, *args)
    print(result.stdout, end="")
    if result.returncode != 0:
        raise AssertionError(f"command failed with exit code {result.returncode}")
    return result


def require_nonempty(path: pathlib.Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise AssertionError(f"expected nonempty file: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, type=pathlib.Path)
    parser.add_argument("--occt-version", required=True)
    parser.add_argument("--netgen-version", required=True)
    parser.add_argument("--work", required=True, type=pathlib.Path)
    args = parser.parse_args()

    if args.work.exists():
        shutil.rmtree(args.work)
    args.work.mkdir(parents=True)

    version = run(args.exe, "ver", "-v", "1").stdout
    if f"OCCT {args.occt_version}" not in version:
        raise AssertionError(f"OCCT version missing from output: {version!r}")
    if f"Netgen v{args.netgen_version}" not in version:
        raise AssertionError(f"Netgen runtime version missing from output: {version!r}")

    brep = args.work / "block.brep"
    stl = args.work / "block.stl"
    run(
        args.exe,
        "block",
        "0",
        "2",
        "0",
        "1",
        "0",
        "1",
        "-o",
        str(brep),
        str(stl),
    )
    require_nonempty(brep)
    require_nonempty(stl)

    vol = args.work / "block.vol"
    mesh = run(
        args.exe,
        "mesh",
        str(brep),
        "-hmax",
        "0.35",
        "-o",
        str(vol),
    ).stdout
    require_nonempty(vol)

    match = re.search(r"mesh points=(\d+) surface=(\d+) volume=(\d+)", mesh)
    if not match:
        raise AssertionError(f"mesh summary missing from output: {mesh!r}")
    if any(int(value) <= 0 for value in match.groups()):
        raise AssertionError(f"mesh summary contains empty topology: {match.groups()}")

    print("geomtool mock end-to-end SDK test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
