#!/usr/bin/env python3
import argparse
import hashlib
import os
import pathlib
import shutil
import tarfile
import urllib.request
import zipfile


RELEASES = {
    "linux": {
        "occt": (
            "https://github.com/precise-simulation/OCCT-sdk/releases/download/"
            "occt-sdk-8.0.1/"
            "opencascade-8.0.1-linux-x86_64-glibc2.17-shared-b8f597c67781.tar.gz",
            "9410d0d7c3e4438d4a71ac751a09ab82bdb963fc8478d0d9635fee27292e3ebb",
        ),
        "netgen": (
            "https://github.com/precise-simulation/netgen-sdk/releases/download/"
            "netgen-sdk-a4ddfe975002-r1/"
            "netgen-featool-v6.2.2608-a4ddfe975002-occt8.0.1-"
            "linux-x86_64-glibc2.17-gcc10.tar.gz",
            "25d5580d121e3fceca7796ed64323de5b2e5efa1a6e7d1fc1a918b89140937e7",
        ),
    },
    "macos-arm64": {
        "occt": (
            "https://github.com/precise-simulation/OCCT-sdk/releases/download/"
            "occt-sdk-8.0.1/"
            "opencascade-8.0.1-macos13-arm64-shared-b8f597c67781.tar.gz",
            "05d428a7ce58703078af39e53d10e2b509f95eb743c7fb4531c8314b6779f46a",
        ),
        "netgen": (
            "https://github.com/precise-simulation/netgen-sdk/releases/download/"
            "netgen-sdk-a4ddfe975002-r1/"
            "netgen-featool-v6.2.2608-a4ddfe975002-occt8.0.1-"
            "macos13-arm64-clang.tar.gz",
            "a9e406bd7d983b010cfe9478a237bcf61e2ee7a6973e5996d294b87ed9f6616f",
        ),
    },
    "windows": {
        "occt": (
            "https://github.com/precise-simulation/OCCT-sdk/releases/download/"
            "occt-sdk-8.0.1/"
            "opencascade-8.0.1-windows-x86_64-vc143-shared-lean-b8f597c67781.zip",
            "160a15bc4134b4468693d1d61c5483774bf865b35da06093843aa69bbac97173",
        ),
        "netgen": (
            "https://github.com/precise-simulation/netgen-sdk/releases/download/"
            "netgen-sdk-a4ddfe975002-r1/"
            "netgen-featool-v6.2.2608-a4ddfe975002-occt8.0.1-win64-msvc.zip",
            "2da605814cd6ba105c4c2b9f66b95eb1b71024a2a4bb8428d10367779efe5d1b",
        ),
    },
}


def download(url: str, digest: str, destination: pathlib.Path) -> None:
    if destination.exists():
        destination.unlink()
    with urllib.request.urlopen(url) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    actual = hashlib.sha256(destination.read_bytes()).hexdigest()
    if actual != digest:
        raise RuntimeError(
            f"SHA-256 mismatch for {destination.name}: expected {digest}, got {actual}"
        )


def extract(archive: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as package:
            package.extractall(destination)
    else:
        with tarfile.open(archive, "r:gz") as package:
            package.extractall(destination)

    roots = [path for path in destination.iterdir() if path.is_dir()]
    files = [path for path in destination.iterdir() if path.is_file()]
    if len(roots) == 1 and not files:
        return roots[0].resolve()
    return destination.resolve()


def append(path: str | None, line: str) -> None:
    if not path:
        return
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=sorted(RELEASES), required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--github-output")
    parser.add_argument("--github-env")
    parser.add_argument("--github-path")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    roots: dict[str, pathlib.Path] = {}
    for name, (url, digest) in RELEASES[args.platform].items():
        suffix = ".zip" if url.endswith(".zip") else ".tar.gz"
        archive = args.output / f"{name}{suffix}"
        download(url, digest, archive)
        roots[name] = extract(archive, args.output / name)

    occt_root = roots["occt"]
    netgen_root = roots["netgen"]
    print(f"OCCT_ROOT={occt_root}")
    print(f"NETGEN_DIR={netgen_root}")
    append(args.github_output, f"occt_root={occt_root}")
    append(args.github_output, f"netgen_dir={netgen_root}")

    if args.platform == "windows":
        append(args.github_path, str(occt_root / "win64" / "vc14" / "bin"))
        append(args.github_path, str(netgen_root / "bin"))
    else:
        runtime = os.pathsep.join([str(occt_root / "lib"), str(netgen_root / "lib")])
        append(args.github_env, f"LD_LIBRARY_PATH={runtime}")
        append(args.github_env, f"DYLD_LIBRARY_PATH={runtime}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
