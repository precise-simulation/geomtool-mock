#!/usr/bin/env python3
import argparse
import gzip
import hashlib
import os
import pathlib
import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile


def copy_runtime_files(
    platform: str,
    stage: pathlib.Path,
    occt_root: pathlib.Path,
    netgen_root: pathlib.Path,
) -> None:
    if platform == "windows":
        sources = [
            (occt_root / "win64" / "vc14" / "bin", "*.dll"),
            (netgen_root / "bin", "*.dll"),
        ]
    elif platform == "linux":
        sources = [
            (occt_root / "lib", "*.so*"),
            (netgen_root / "lib", "*.so*"),
        ]
    elif platform == "macos":
        sources = [
            (occt_root / "lib", "*.dylib"),
            (netgen_root / "lib", "*.dylib"),
        ]
    else:
        raise ValueError(f"unsupported platform: {platform}")

    copied: dict[str, str] = {}
    for directory, pattern in sources:
        for source in sorted(directory.glob(pattern)):
            if not source.is_file() and not source.is_symlink():
                continue
            resolved = source.resolve()
            digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
            if source.name in copied and copied[source.name] != digest:
                raise RuntimeError(f"conflicting runtime basename: {source.name}")
            copied[source.name] = digest
            destination = stage / source.name
            if not destination.exists():
                shutil.copy2(resolved, destination)


def patch_macos(stage: pathlib.Path, executable: pathlib.Path) -> None:
    binaries = [executable, *sorted(stage.glob("*.dylib"))]
    staged_names = {path.name for path in binaries}
    for binary in binaries:
        result = subprocess.run(
            ["otool", "-L", str(binary)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )
        for line in result.stdout.splitlines()[1:]:
            dependency = line.strip().split(" ", 1)[0]
            if not dependency:
                continue
            name = pathlib.Path(dependency).name
            if name in staged_names and dependency != f"@loader_path/{name}":
                subprocess.run(
                    [
                        "install_name_tool",
                        "-change",
                        dependency,
                        f"@loader_path/{name}",
                        str(binary),
                    ],
                    check=True,
                )
        if binary.suffix == ".dylib":
            subprocess.run(
                ["install_name_tool", "-id", f"@loader_path/{binary.name}", str(binary)],
                check=True,
            )


def make_tar(stage: pathlib.Path, archive: pathlib.Path) -> None:
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(
                fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT
            ) as package:
                for source in sorted(stage.iterdir(), key=lambda path: path.name):
                    info = tarfile.TarInfo(source.name)
                    info.size = source.stat().st_size
                    info.mtime = 0
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mode = (
                        0o755
                        if source.name == "geomtool" or os.access(source, os.X_OK)
                        else 0o644
                    )
                    with source.open("rb") as payload:
                        package.addfile(info, payload)


def make_zip(stage: pathlib.Path, archive: pathlib.Path) -> None:
    with zipfile.ZipFile(
        archive, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as package:
        for source in sorted(stage.iterdir(), key=lambda path: path.name):
            info = zipfile.ZipInfo(source.name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o755) << 16
            package.writestr(info, source.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, type=pathlib.Path)
    parser.add_argument("--platform", choices=("windows", "linux", "macos"), required=True)
    parser.add_argument("--occt-root", required=True, type=pathlib.Path)
    parser.add_argument("--netgen-dir", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args()

    if not args.exe.is_file():
        raise FileNotFoundError(args.exe)
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / args.package_name
    if archive.exists():
        archive.unlink()

    with tempfile.TemporaryDirectory(prefix="geomtool-package-") as temporary:
        stage = pathlib.Path(temporary)
        executable_name = "geomtool.exe" if args.platform == "windows" else "geomtool"
        executable = stage / executable_name
        shutil.copy2(args.exe, executable)
        executable.chmod(0o755)

        if not args.static:
            copy_runtime_files(
                args.platform, stage, args.occt_root.resolve(), args.netgen_dir.resolve()
            )
            if args.platform == "macos":
                patch_macos(stage, executable)

        if args.platform == "windows":
            if not args.package_name.endswith(".zip"):
                raise ValueError("Windows package name must end in .zip")
            make_zip(stage, archive)
        else:
            if not args.package_name.endswith(".tar.gz"):
                raise ValueError("Unix package name must end in .tar.gz")
            make_tar(stage, archive)

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(archive)
    print(sidecar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
