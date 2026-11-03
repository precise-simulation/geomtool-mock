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
    parser.add_argument("--work", required=True, type=pathlib.Path)
    parser.add_argument("--mesh", action="store_true")
    args = parser.parse_args()

    if args.work.exists():
        shutil.rmtree(args.work)
    args.work.mkdir(parents=True)

    version = run(args.exe, "ver", "-v", "1").stdout
    if not version.strip():
        raise AssertionError("version command produced no output")

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

    if args.mesh:
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
        if match and any(int(value) <= 0 for value in match.groups()):
            raise AssertionError(f"mesh summary contains empty topology: {match.groups()}")

    print("geomtool compatibility end-to-end test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
