# Geomtool release skeleton

This repository is a source-independent build and release skeleton for
Geomtool. It intentionally does not contain the real Geomtool implementation,
but it mirrors the native build boundary closely enough that the real source
tree can replace the mock source tree without changing the release machinery.

The designated binary SDK producers are:

- `precise-simulation/OCCT-sdk` release `occt-sdk-8.0.1`
- `precise-simulation/netgen-sdk` release `netgen-sdk-a4ddfe975002-r1`

All SDK archives are pinned by SHA-256 in `scripts/fetch_sdks.py`.

## Drop-in source contract

`CMakeLists.txt` uses the same native source graph and build switches as full
Geomtool:

- base sources: `export.cpp`, `geom.cpp`, `geom_ops.cpp`,
  `geom_util.cpp`, `gobj.cpp`, `import.cpp`, `main.cpp`,
  `shapemap.cpp`, and `util.cpp`
- Netgen sources: `mesh.cpp` and `mesh_netgen.cpp`
- InstantMesh2D sources: `mesh.cpp`, `mesh_instant.cpp`, and the three
  `third_party/instantmesh2d` translation units
- build inputs: `USE_MESH`, `USE_INSTANTMESH2D`, `STATIC`, `BUILDNO`,
  `OCCT_ROOT`, `NETGEN_DIR`, `OCC_INC_DIR`, `OCC_LIB_DIR`, and
  `OpenCASCADE_DIR`

The mock files under `src/` and `third_party/instantmesh2d/` exist only to
exercise that graph. Replacing those directories with the corresponding real
Geomtool sources is the intended compatibility test; CI and packaging should
not need source-specific edits.

The mock executable keeps three real integration operations:

- `geomtool ver -v 1`
- `geomtool block ... -o block.brep block.stl`, using OCCT
- `geomtool mesh block.brep -hmax 0.35 -o block.vol`, using Netgen's OCC API

## Native release qualification

`.github/workflows/native-release.yml` builds release packages on GitHub
Actions only. It produces the same 14 package names used by the full native
Geomtool release contract:

- Windows x86_64 shared: Netgen-only and Netgen + InstantMesh2D
- Linux x86_64 glibc 2.17 / GCC 10 shared: both variants
- macOS 13 x86_64 shared: both variants
- macOS 13 arm64 shared: both variants
- Linux x86_64 static SDK closure: both variants
- macOS 13 x86_64 static SDK closure: both variants
- macOS 13 arm64 static SDK closure: both variants

Linux builds run inside the pinned manylinux2014 producer image and retain the
`_GLIBCXX_USE_CXX11_ABI=0` compatibility flag used by the full Geomtool
pipeline. macOS builds target macOS 13.0 with Xcode 16.4. Windows uses the
GitHub-hosted VS2022 worker.

Every job:

1. downloads and SHA-256 verifies the designated SDK archives;
2. builds Netgen-only and combined `geomtool` executables;
3. executes the build-tree binary;
4. creates a deterministic `.zip` or `.tar.gz` plus `.sha256`;
5. extracts the final package and executes the packaged binary again; and
6. uploads the qualified package pair as a GitHub Actions artifact.

Shared packages contain the executable and SDK runtime libraries at archive
root. Static packages contain the executable only. Runtime packages reject
development headers and static/import libraries during verification.

`.github/workflows/release.yml` is a reusable release orchestrator. A
`v*` tag or a manual dispatch from `main` first invokes the complete native
qualification matrix, verifies the exact 14-package artifact set and every
SHA-256 sidecar, then publishes those files to the GitHub Release matching
`src/globals.hpp`'s `VERSION`.

No CircleCI configuration is used.

## Local build

For a Windows shared combined build with extracted SDKs:

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 `
  "-DBUILDNO:STRING=26.11.0" `
  -DUSE_MESH=ON `
  -DUSE_INSTANTMESH2D=ON `
  "-DOCCT_ROOT=C:\path\to\occt-sdk" `
  "-DNETGEN_DIR=C:\path\to\netgen-sdk"
cmake --build build --config Release --parallel --target geomtool
ctest --test-dir build -C Release --output-on-failure
```

To fetch the exact SDK pair used by one CI matrix entry:

```sh
python3 scripts/fetch_sdks.py --platform linux --output .deps
```

Supported keys are `windows`, `linux`, `macos-x86_64`,
`macos-arm64`, and their `-static` variants.
