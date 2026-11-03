#!/usr/bin/env python3
import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tarfile
import zipfile


def extract(archive: pathlib.Path, destination: pathlib.Path) -> None:
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as package:
            package.extractall(destination)
    else:
        with tarfile.open(archive, "r:gz") as package:
            package.extractall(destination, filter="fully_trusted")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=pathlib.Path)
    parser.add_argument("--work", required=True, type=pathlib.Path)
    parser.add_argument("--mesh", action="store_true")
    args = parser.parse_args()

    sidecar = args.archive.with_name(args.archive.name + ".sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = hashlib.sha256(args.archive.read_bytes()).hexdigest()
    if actual != expected:
        raise AssertionError(
            f"package checksum mismatch: expected {expected}, got {actual}"
        )

    if args.work.exists():
        shutil.rmtree(args.work)
    args.work.mkdir(parents=True)
    extract(args.archive, args.work)

    executable = args.work / (
        "geomtool.exe" if args.archive.name.endswith(".zip") else "geomtool"
    )
    if not executable.is_file():
        raise AssertionError(f"package lacks root executable: {executable.name}")
    if executable.name == "geomtool":
        executable.chmod(0o755)

    forbidden = {".h", ".hpp", ".cpp", ".cxx", ".cc", ".c", ".a", ".lib"}
    development_files = [
        path.name
        for path in args.work.iterdir()
        if path.is_file() and path.suffix.lower() in forbidden
    ]
    if development_files:
        raise AssertionError(
            f"runtime package contains development files: {development_files}"
        )

    command = [
        sys.executable,
        str(pathlib.Path(__file__).resolve().parents[1] / "tests" / "e2e.py"),
        "--exe",
        str(executable),
        "--work",
        str(args.work / "smoke"),
    ]
    if args.mesh:
        command.append("--mesh")
    subprocess.run(command, check=True)
    print(f"verified packaged runtime: {args.archive.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
