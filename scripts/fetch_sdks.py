#!/usr/bin/env python3
import argparse
import hashlib
import os
import pathlib
import shutil
import tarfile
import urllib.request
import zipfile


OCCT_BASE = (
    "https://github.com/precise-simulation/OCCT-sdk/releases/download/"
    "occt-sdk-8.0.1/"
)
NETGEN_BASE = (
    "https://github.com/precise-simulation/netgen-sdk/releases/download/"
    "netgen-sdk-2acc7e8443a4-r1/"
)


RELEASES = {
    "linux": {
        "occt": (
            OCCT_BASE
            + "opencascade-8.0.1-linux-x86_64-glibc2.17-shared-b8f597c67781.tar.gz",
            "9410d0d7c3e4438d4a71ac751a09ab82bdb963fc8478d0d9635fee27292e3ebb",
        ),
        "netgen": (
            NETGEN_BASE
            + "netgen-featool-v6.2.2608-2acc7e8443a4-occt8.0.1-"
            "linux-x86_64-glibc2.17-gcc10.tar.gz",
            "71cf2fe7d7930afb8f23c81f0364b5b35f0dee3f805acd19615492a7ec32b867",
        ),
    },
    "linux-static": {
        "occt": (
            OCCT_BASE
            + "opencascade-8.0.1-linux-x86_64-glibc2.17-static-b8f597c67781.tar.gz",
            "6089d212ee87589c41ed7818056e064c5fc6a1e75ed8463d5f266d8f18588815",
        ),
        "netgen": (
            NETGEN_BASE
            + "netgen-featool-v6.2.2608-2acc7e8443a4-occt8.0.1-"
            "linux-x86_64-glibc2.17-gcc10-static.tar.gz",
            "5ad838a7bb94b22dc85c47852b17f2a023851de5a59636cba225161aac7e043a",
        ),
    },
    "macos-arm64": {
        "occt": (
            OCCT_BASE
            + "opencascade-8.0.1-macos13-arm64-shared-b8f597c67781.tar.gz",
            "05d428a7ce58703078af39e53d10e2b509f95eb743c7fb4531c8314b6779f46a",
        ),
        "netgen": (
            NETGEN_BASE
            + "netgen-featool-v6.2.2608-2acc7e8443a4-occt8.0.1-"
            "macos13-arm64-clang.tar.gz",
            "bfb3be5afee3ce9f7d9e40643f74d6fc8c0330912e437ac84d3adaae61d8c380",
        ),
    },
    "macos-arm64-static": {
        "occt": (
            OCCT_BASE
            + "opencascade-8.0.1-macos13-arm64-static-b8f597c67781.tar.gz",
            "5e622423378d3e9b0e9a4003d8f107829fe1c4accb8a2527b072cdb6514cf615",
        ),
        "netgen": (
            NETGEN_BASE
            + "netgen-featool-v6.2.2608-2acc7e8443a4-occt8.0.1-"
            "macos13-arm64-clang-static.tar.gz",
            "0d46336fe9f5255595eecbda069e6a6df8bef52abc695fce93ad4cce55c10959",
        ),
    },
    "macos-x86_64": {
        "occt": (
            OCCT_BASE
            + "opencascade-8.0.1-macos13-x86_64-shared-b8f597c67781.tar.gz",
            "20c18138d5cee57949984e4247ef7f6bdbf5b41f821cc7e2cdc6f8fca454a1b2",
        ),
        "netgen": (
            NETGEN_BASE
            + "netgen-featool-v6.2.2608-2acc7e8443a4-occt8.0.1-"
            "macos13-x86_64-clang.tar.gz",
            "e41f398a26e8f1895be6bcbfa86a85ea58fbcccb61738ca64361dd55fb6cc75d",
        ),
    },
    "macos-x86_64-static": {
        "occt": (
            OCCT_BASE
            + "opencascade-8.0.1-macos13-x86_64-static-b8f597c67781.tar.gz",
            "2af40d7a2389445fb2e2670c7ea533504b67b872ec0d00d0313bc20237b52f55",
        ),
        "netgen": (
            NETGEN_BASE
            + "netgen-featool-v6.2.2608-2acc7e8443a4-occt8.0.1-"
            "macos13-x86_64-clang-static.tar.gz",
            "b40c95988f8fd53d5dfba3350e9b800ac0d0b1feb28ebd1e28104be042e92a27",
        ),
    },
    "windows": {
        "occt": (
            OCCT_BASE
            + "opencascade-8.0.1-windows-x86_64-vc143-shared-lean-b8f597c67781.zip",
            "160a15bc4134b4468693d1d61c5483774bf865b35da06093843aa69bbac97173",
        ),
        "netgen": (
            NETGEN_BASE
            + "netgen-featool-v6.2.2608-2acc7e8443a4-occt8.0.1-win64-msvc.zip",
            "819c0abd970e400a24943940162a3792698e7107ae0790312485ae79b35a8c90",
        ),
    },
    "windows-static": {
        "occt": (
            OCCT_BASE
            + "opencascade-8.0.1-windows-x86_64-vc143-static-lean-b8f597c67781.zip",
            "7e0a80a971cfb3badf7a25cb2218a16fb61a196de52506537f21da6e044809f2",
        ),
        "netgen": (
            NETGEN_BASE
            + "netgen-featool-v6.2.2608-2acc7e8443a4-occt8.0.1-win64-msvc-static.zip",
            "b503ab285423f863832bee4142295639df52279c95c3457e5961f6361c8801b6",
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
            package.extractall(destination, filter="fully_trusted")

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
    elif not args.platform.endswith("-static"):
        runtime = os.pathsep.join([str(occt_root / "lib"), str(netgen_root / "lib")])
        append(args.github_env, f"LD_LIBRARY_PATH={runtime}")
        append(args.github_env, f"DYLD_LIBRARY_PATH={runtime}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
