#!/usr/bin/env python3
import argparse
import json
import pathlib
import re
import sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / ".github" / "geomtool-native-contract.json"


def load_contract(source: str) -> dict:
    return json.loads(pathlib.Path(source).read_text(encoding="utf-8-sig"))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def cmake_set_items(text: str, variable: str) -> list[str]:
    match = re.search(rf"set\(\s*{re.escape(variable)}\s+(.*?)\n\s*\)", text, re.S)
    if not match:
        return []
    return re.findall(r"[A-Za-z0-9_]+", match.group(1))


def yaml_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(key)}:\s*['\"]?([^'\"\s#]+)", text, re.M)
    return match.group(1) if match else None


def expected_runner(contract: dict, entry: dict) -> str:
    platform = entry["platform"]
    if platform == "windows":
        return contract["toolchains"]["windows"]["runner"]
    if platform == "linux":
        return contract["toolchains"]["linux"]["runner"]
    if platform == "macos":
        key = "x86_64_runner" if entry["arch"] == "x86_64" else "arm64_runner"
        return contract["toolchains"]["macos"][key]
    raise ValueError(f"unsupported matrix platform: {platform}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    args = parser.parse_args()

    contract = load_contract(args.contract)
    errors: list[str] = []
    if contract.get("owner") != "precise-simulation/geomtool":
        fail(errors, "contract owner is not precise-simulation/geomtool")
    if contract.get("schema") != 1:
        fail(errors, f"unsupported native contract schema: {contract.get('schema')!r}")

    cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    cmake_contract = contract["cmake"]
    if f"cmake_minimum_required(VERSION {cmake_contract['minimum_version']})" not in cmake:
        fail(errors, "CMake minimum version differs from Geomtool native contract")
    if f'CMAKE_MSVC_RUNTIME_LIBRARY "{cmake_contract["msvc_runtime"]}"' not in cmake:
        fail(errors, "MSVC runtime differs from Geomtool native contract")
    if f"CXX_STANDARD {cmake_contract['cxx_standard']}" not in cmake:
        fail(errors, "C++ standard differs from Geomtool native contract")
    for name in cmake_contract["inputs"]:
        if not re.search(rf"\b{re.escape(name)}\b", cmake):
            fail(errors, f"CMake input {name} is missing")
    actual_occt = cmake_set_items(cmake, "OCC_LIBS")
    if actual_occt != cmake_contract["occt_libraries"]:
        fail(errors, f"OCC_LIBS differs from Geomtool: {actual_occt!r}")
    linkage = cmake_contract["linkage"]
    linkage_checks = {
        "shared_occt": (
            "explicit_library_files",
            [
                "find_library(OCC_LIBRARY_${libname} NAMES ${libname}",
                'assert_in_occt_root("OCCT library ${libname}" "${OCC_LIBRARY_${libname}}")',
                'list(APPEND OCC_LIBRARIES "${OCC_LIBRARY_${libname}}")',
            ],
        ),
        "static_windows_occt": (
            "package_library_list",
            ["if(STATIC AND WIN32)", "set(OCC_LIBRARIES ${OpenCASCADE_LIBRARIES})"],
        ),
        "static_unix_occt": (
            "explicit_imported_targets",
            ["elseif(STATIC)", "list(APPEND OCC_LIBRARIES ${libname})"],
        ),
        "static_netgen": (
            "whole_archive_nglib",
            [
                '"/WHOLEARCHIVE:${NETGEN_NGLIB_LIBRARY}"',
                '"-Wl,-force_load,${NETGEN_NGLIB_LIBRARY}"',
                '"-Wl,--whole-archive" "${NETGEN_NGLIB_LIBRARY}" "-Wl,--no-whole-archive"',
            ],
        ),
    }
    for key, (expected_policy, snippets) in linkage_checks.items():
        if linkage.get(key) != expected_policy:
            fail(errors, f"unsupported Geomtool linkage policy {key}={linkage.get(key)!r}")
            continue
        for snippet in snippets:
            if snippet not in cmake:
                fail(errors, f"CMake linkage policy {key} differs from Geomtool")

    for relative, variables in contract["source_manifests"].items():
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        for variable in variables:
            if not re.search(rf"set\(\s*{re.escape(variable)}\b", text):
                fail(errors, f"{relative} does not define required Geomtool interface variable {variable}")

    matrix_path = ROOT / ".github" / "native-release-matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    shared_fields = ("id", "runner", "platform", "static", "package_base", "extension")
    local_matrix = [
        {field: entry[field] for field in shared_fields}
        | {"arch": "x86_64" if "x86_64" in entry["id"] or entry["platform"] != "macos" else "arm64"}
        for entry in matrix.get("include", [])
    ]
    if local_matrix != contract["matrix"]["include"]:
        fail(errors, ".github/native-release-matrix.json differs from Geomtool native contract")
    for entry in contract["matrix"]["include"]:
        runner = expected_runner(contract, entry)
        if entry["runner"] != runner:
            fail(errors, f"Geomtool native contract has inconsistent runner for {entry['id']}")

    workflow_path = ROOT / ".github" / "workflows" / "native-release.yml"
    workflow = workflow_path.read_text(encoding="utf-8")
    linux = contract["toolchains"]["linux"]
    expected_scalars = {
        "PRODUCER_IMAGE": linux["producer_image"],
        "PRODUCER_IMAGE_TAG": linux["producer_image_tag"],
        "PRODUCER_IMAGE_DIGEST": linux["producer_image_digest"],
        "CMAKE_VERSION": linux["cmake_version"],
    }
    for key, expected in expected_scalars.items():
        actual = yaml_scalar(workflow, key)
        if actual != expected:
            fail(errors, f"native-release.yml {key} differs: expected {expected!r}, got {actual!r}")
    abi = linux["glibcxx_cxx11_abi"]
    if f"_GLIBCXX_USE_CXX11_ABI={abi}" not in workflow:
        fail(errors, "Linux libstdc++ ABI differs from Geomtool native contract")
    macos = contract["toolchains"]["macos"]
    if f' MACOSX_DEPLOYMENT_TARGET: "{macos["deployment_target"]}"'.strip() not in workflow:
        fail(errors, "macOS deployment target differs from Geomtool native contract")
    xcode = macos["xcode_version"]
    if f"Xcode_{xcode}.app" not in workflow:
        fail(errors, "Xcode version differs from Geomtool native contract")

    baseline = contract["sdk_baseline"]
    fetcher = (ROOT / "scripts" / "fetch_sdks.py").read_text(encoding="utf-8")
    match = re.search(r'^DEFAULT_NETGEN_RELEASE\s*=\s*"([^"]+)"', fetcher, re.M)
    actual_default = match.group(1) if match else None
    if actual_default != baseline["netgen_release"]:
        fail(
            errors,
            "default Netgen SDK baseline differs from Geomtool native contract: "
            f"expected {baseline['netgen_release']!r}, got {actual_default!r}",
        )
    if workflow.count(baseline["netgen_release"]) < 3:
        fail(errors, "native-release.yml does not consistently use the Geomtool Netgen baseline")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("geomtool-mock matches the Geomtool native compatibility contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
