#!/usr/bin/env python3
import argparse
import base64
import fnmatch
import hashlib
import json
import os
import pathlib
import shutil
import tarfile
import urllib.parse
import urllib.request
import zipfile


DEFAULT_NETGEN_RELEASE = "netgen-sdk-2acc7e8443a4-r1"
NETGEN_REPOSITORY = "precise-simulation/netgen-sdk"
OCCT_REPOSITORY = "precise-simulation/OCCT-sdk"

ASSET_PATTERNS = {
    "linux": {
        "occt": "opencascade-*-linux-x86_64-glibc2.17-shared-*.tar.gz",
        "netgen": "netgen-featool-v*-*-occt*-linux-x86_64-glibc2.17-gcc10.tar.gz",
    },
    "linux-static": {
        "occt": "opencascade-*-linux-x86_64-glibc2.17-static-*.tar.gz",
        "netgen": "netgen-featool-v*-*-occt*-linux-x86_64-glibc2.17-gcc10-static.tar.gz",
    },
    "macos-arm64": {
        "occt": "opencascade-*-macos13-arm64-shared-*.tar.gz",
        "netgen": "netgen-featool-v*-*-occt*-macos13-arm64-clang.tar.gz",
    },
    "macos-arm64-static": {
        "occt": "opencascade-*-macos13-arm64-static-*.tar.gz",
        "netgen": "netgen-featool-v*-*-occt*-macos13-arm64-clang-static.tar.gz",
    },
    "macos-x86_64": {
        "occt": "opencascade-*-macos13-x86_64-shared-*.tar.gz",
        "netgen": "netgen-featool-v*-*-occt*-macos13-x86_64-clang.tar.gz",
    },
    "macos-x86_64-static": {
        "occt": "opencascade-*-macos13-x86_64-static-*.tar.gz",
        "netgen": "netgen-featool-v*-*-occt*-macos13-x86_64-clang-static.tar.gz",
    },
    "windows": {
        "occt": "opencascade-*-windows-x86_64-vc143-shared-lean-*.zip",
        "netgen": "netgen-featool-v*-*-occt*-win64-msvc.zip",
    },
    "windows-static": {
        "occt": "opencascade-*-windows-x86_64-vc143-static-lean-*.zip",
        "netgen": "netgen-featool-v*-*-occt*-win64-msvc-static.zip",
    },
}


def github_json(path: str) -> dict:
    url = f"https://api.github.com/{path.lstrip('/')}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def release(repository: str, tag: str) -> dict:
    data = github_json(
        f"repos/{repository}/releases/tags/{urllib.parse.quote(tag, safe='')}"
    )
    if data.get("draft") or data.get("prerelease") or data.get("immutable") is not True:
        raise RuntimeError(f"{repository} {tag} is not a published immutable release")
    return data


def paired_occt_release(netgen_release: str) -> str:
    data = github_json(
        "repos/"
        f"{NETGEN_REPOSITORY}/contents/.github/occt-sdk-release.txt"
        f"?ref={urllib.parse.quote(netgen_release, safe='')}"
    )
    content = base64.b64decode(data["content"]).decode("utf-8").strip()
    if not content.startswith("occt-sdk-"):
        raise RuntimeError(
            f"{NETGEN_REPOSITORY} {netgen_release} has invalid OCCT release pin: {content}"
        )
    return content


def asset(release_data: dict, pattern: str) -> tuple[str, str, int]:
    matches = [
        candidate
        for candidate in release_data.get("assets", [])
        if fnmatch.fnmatch(candidate.get("name", ""), pattern)
        and not candidate.get("name", "").endswith(".sha256")
    ]
    if len(matches) != 1:
        names = [candidate.get("name", "") for candidate in matches]
        raise RuntimeError(
            f"expected exactly one asset matching {pattern!r}, found {names}"
        )
    candidate = matches[0]
    digest = candidate.get("digest", "")
    if not digest.startswith("sha256:"):
        raise RuntimeError(f"{candidate['name']} does not have a GitHub SHA-256 digest")
    return candidate["browser_download_url"], digest.removeprefix("sha256:"), candidate["size"]


def download(url: str, digest: str, size: int, destination: pathlib.Path) -> None:
    if destination.exists():
        destination.unlink()
    with urllib.request.urlopen(url) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    actual = hashlib.sha256(destination.read_bytes()).hexdigest()
    if actual != digest:
        raise RuntimeError(
            f"SHA-256 mismatch for {destination.name}: expected {digest}, got {actual}"
        )
    if destination.stat().st_size != size:
        raise RuntimeError(
            f"size mismatch for {destination.name}: expected {size}, "
            f"got {destination.stat().st_size}"
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
    parser.add_argument("--platform", choices=sorted(ASSET_PATTERNS), required=True)
    parser.add_argument("--netgen-release", default=DEFAULT_NETGEN_RELEASE)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--github-output")
    parser.add_argument("--github-env")
    parser.add_argument("--github-path")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    netgen_release = release(NETGEN_REPOSITORY, args.netgen_release)
    occt_release_tag = paired_occt_release(args.netgen_release)
    occt_release = release(OCCT_REPOSITORY, occt_release_tag)

    roots: dict[str, pathlib.Path] = {}
    releases = {"occt": occt_release, "netgen": netgen_release}
    for name, pattern in ASSET_PATTERNS[args.platform].items():
        url, digest, size = asset(releases[name], pattern)
        suffix = ".zip" if url.endswith(".zip") else ".tar.gz"
        archive = args.output / f"{name}{suffix}"
        download(url, digest, size, archive)
        roots[name] = extract(archive, args.output / name)

    occt_root = roots["occt"]
    netgen_root = roots["netgen"]
    print(f"OCCT_ROOT={occt_root}")
    print(f"NETGEN_DIR={netgen_root}")
    print(f"OCCT_RELEASE={occt_release_tag}")
    print(f"NETGEN_RELEASE={args.netgen_release}")
    append(args.github_output, f"occt_root={occt_root}")
    append(args.github_output, f"netgen_dir={netgen_root}")
    append(args.github_output, f"occt_release={occt_release_tag}")
    append(args.github_output, f"netgen_release={args.netgen_release}")

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
