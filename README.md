# Geomtool SDK mock

This repository is a source-independent integration mock for the Geomtool build
boundary. It does not contain or copy Geomtool implementation sources.

The mock builds a small executable named `geomtool` against the designated
binary SDK releases:

- `precise-simulation/OCCT-sdk` release `occt-sdk-8.0.1`
- `precise-simulation/netgen-sdk` release `netgen-sdk-a4ddfe975002-r1`

The executable deliberately implements only the integration surface needed for
end-to-end dependency validation:

- `geomtool ver -v 1` reports the linked OCCT baseline and the runtime Netgen
  library version.
- `geomtool block ... -o box.brep box.stl` constructs a real OCCT box and
  writes BREP and STL files.
- `geomtool mesh box.brep -hmax 0.35 -o box.vol` loads the BREP through the
  Netgen OCC API, generates edge, surface, and volume meshes, and writes a
  Netgen VOL mesh.

The end-to-end test requires all generated files to be nonempty and requires
Netgen to report positive point, surface-element, and volume-element counts.
This catches SDK packaging, linking, runtime-loading, OCCT interoperability, and
basic Netgen meshing failures without depending on Geomtool sources.

## GitHub Actions

`.github/workflows/build-test.yml` is the supported build/test execution path.
It runs on GitHub-hosted Linux x86_64, macOS arm64, and Windows x86_64 workers.
Each job downloads the pinned shared SDK archives from the two designated SDK
repositories, verifies their SHA-256 digests, configures CMake, builds the mock,
and runs the end-to-end test.

No CircleCI configuration is used.

## Local configuration

If the matching SDK archives are already extracted:

```sh
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DOCCT_ROOT=/path/to/occt-sdk \
  -DNETGEN_DIR=/path/to/netgen-sdk
cmake --build build --config Release --parallel --target geomtool
ctest --test-dir build -C Release --output-on-failure
```

For convenience, `scripts/fetch_sdks.py` downloads and verifies the exact SDK
archives used by CI:

```sh
python3 scripts/fetch_sdks.py --platform linux --output .deps
```

Supported platform keys are `linux`, `macos-arm64`, and `windows`.
