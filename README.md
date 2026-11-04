# Geomtool SDK compatibility canary

This repository is a native SDK compatibility canary and release-contract test
fixture for Geomtool. It intentionally does not contain the real Geomtool
implementation. Instead, it exercises the same OCCT/Netgen integration boundary,
native platform matrix, packaging shape, and staged-package checks used to detect
dependency or release-contract regressions before they reach production Geomtool.

The designated binary SDK producers are:

- `precise-simulation/OCCT-sdk`
- `precise-simulation/netgen-sdk`

Normal pull-request and manual qualification defaults to the known-good
`netgen-sdk-2acc7e8443a4-r1` baseline. The exact OCCT SDK release is read from
that Netgen SDK release's `.github/occt-sdk-release.txt` pin. SDK archives are
resolved from their published immutable GitHub Releases and verified against
GitHub's SHA-256 digest and asset size before extraction.

## Shared native contract

`src/sources.cmake` and `third_party/instantmesh2d/sources.cmake` own the native
source graph. Production Geomtool owns the machine-readable shared contract in
`.github/native-contract.json`; `scripts/check_geomtool_contract.py` reads the
current `precise-simulation/geomtool` `main` contract and verifies that this
fixture still matches it. `CMakeLists.txt` consumes the manifests with the same
dependency/linkage behavior and build switches as full Geomtool:

- base sources: `export.cpp`, `geom.cpp`, `geom_ops.cpp`,
  `geom_util.cpp`, `gobj.cpp`, `import.cpp`, `main.cpp`,
  `shapemap.cpp`, and `util.cpp`
- Netgen sources: `mesh.cpp` and `mesh_netgen.cpp`
- InstantMesh2D sources: `mesh.cpp`, `mesh_instant.cpp`, and the three
  `third_party/instantmesh2d` translation units
- build inputs: `USE_MESH`, `USE_INSTANTMESH2D`, `STATIC`, `BUILDNO`,
  `OCCT_ROOT`, `NETGEN_DIR`, `OCC_INC_DIR`, `OCC_LIB_DIR`, and
  `OpenCASCADE_DIR`

The shared manifest interface used by top-level CMake is part of the contract.
`src/sources.cmake` defines `GEOMTOOL_BASE_SOURCES`,
`GEOMTOOL_MESH_SOURCES`, `GEOMTOOL_NETGEN_SOURCES`, and
`GEOMTOOL_INSTANTMESH2D_SOURCES`; `third_party/instantmesh2d/sources.cmake`
defines `GEOMTOOL_INSTANTMESH2D_CORE_SOURCES`.

Manual test-release publication also reads the product version directly from
`src/globals.hpp`. The fixture keeps an exact, unindented
definition of the form `#define VERSION "<version>"` on its own line. The
version string is used to construct test release tags.

The mock files under `src/` and `third_party/instantmesh2d/` exist only to
exercise the integration contract; they are not intended to mirror Geomtool's
implementation or semantic qualification suite.

The fixture executable preserves the three integration behaviors used
by `tests/e2e.py` and package qualification:

- `geomtool ver -v 1` exits successfully and prints nonempty version output;
- `geomtool block ... -o block.brep block.stl` exits successfully and produces
  nonempty BREP and STL outputs using OCCT; and
- `geomtool mesh block.brep -hmax 0.35 -o block.vol` exits successfully and
  produces a nonempty Netgen VOL mesh. If it prints the mock-compatible
  `mesh points=<n> surface=<n> volume=<n>` summary, all counts must be positive.

## Native release qualification

`.github/workflows/native-release.yml` builds release packages on GitHub
Actions only. `.github/native-release-matrix.json` is the single package matrix
used by qualification and publication. It produces the same 16 package names
used by the full native Geomtool release contract:

- Windows x86_64 shared and static: Netgen-only and Netgen + InstantMesh2D
- Linux x86_64 glibc 2.17 / GCC 10 shared: both variants
- macOS 13 x86_64 shared: both variants
- macOS 13 arm64 shared: both variants
- Linux x86_64 static SDK closure: both variants
- macOS 13 x86_64 static SDK closure: both variants
- macOS 13 arm64 static SDK closure: both variants

Linux builds run inside the pinned manylinux2014 producer image and retain the
`_GLIBCXX_USE_CXX11_ABI=0` compatibility flag used by the full Geomtool
pipeline. macOS builds target macOS 13.0 with Xcode 16.4. Windows uses the
GitHub-hosted VS2022 worker. Windows static packages retain the `/MD` runtime
contract of the qualified OCCT and Netgen SDKs; top-level CMake supplies the
OCCT static consumer definitions and required Windows system libraries.

Every job:

1. resolves the Netgen SDK release and its exact paired OCCT SDK release, then
   downloads and verifies the designated SDK archives;
2. builds Netgen-only and combined `geomtool` executables;
3. executes the build-tree binary;
4. creates a deterministic `.zip` or `.tar.gz` plus `.sha256`;
5. extracts the final package and executes the packaged binary again; and
6. uploads the qualified package pair as a GitHub Actions artifact.

Shared packages contain the executable and SDK runtime libraries at archive
root. Static packages contain the executable only. Runtime packages reject
development headers and static/import libraries during verification.

`.github/workflows/release.yml` is manual-only. A dispatch from `main` invokes
the complete native qualification matrix,
checks the exact package set derived from `.github/native-release-matrix.json`
and every SHA-256 sidecar, then creates
a draft GitHub prerelease and verifies the uploaded files byte-for-byte before
publishing it. Test tags are unique per run and attempt, with the form
`test-v<VERSION>-<run-id>-<attempt>`; the workflow never claims the production
`v<VERSION>` tag or marks a test release as latest. An existing release is not
overwritten. Pull requests continue to run native qualification without
publishing, and the native workflow can also be dispatched independently.

`.github/workflows/sdk-canary.yml` is the downstream SDK compatibility canary.
Every six hours it checks for the newest published immutable `netgen-sdk-*`
release. Its schedule is offset from the Netgen SDK repository's own periodic
OCCT update check, but there is no cross-repository ordering guarantee; if a
Netgen rebuild finishes later, the following canary poll detects it. The Netgen
release determines the exact OCCT SDK pair. A full native qualification runs
only when that Netgen SDK release has not already passed the scheduled canary;
success is recorded by a `canary-netgen-sdk-*` tag in this repository.

The canary can also be dispatched manually from any selected branch. Its
optional `netgen_release` input selects an exact immutable Netgen SDK release;
an empty value selects the newest release. Manual canary runs always execute and
do not create or update scheduled-canary marker tags, so they can be used to
test Geomtool/mock changes independently of dependency releases. The reusable
**Native geomtool release qualification** workflow is also directly
dispatchable with the same optional Netgen SDK release selection; its default
remains the known-good baseline used by pull requests and normal mock changes.

## Alignment with production Geomtool

Changes are expected in both repositories only when they cross the shared
native compatibility contract. Paired updates are required for:

- CMake dependency/linkage behavior or the shared CMake inputs;
- the explicit OCCT toolkit closure;
- the shared source-manifest variable interface (ordinary source-file membership
  remains repository-local);
- the committed OCCT/Netgen SDK baseline used by normal qualification;
- represented Windows/Linux/macOS runner and toolchain baselines; or
- package names, platform/architecture coverage, and shared/static variants.

Ordinary Geomtool source behavior, detailed production semantic qualification,
release orchestration, publication rules, and production-only runtime consumers
remain Geomtool-only. The mock should not copy those mechanisms merely to look
similar.

Native qualification runs `scripts/check_geomtool_contract.py` before loading
the matrix, so drift from current production `main` fails early. For paired
changes that are still local, validate against a sibling Geomtool checkout:

```sh
python3 scripts/check_geomtool_contract.py \
  --contract ../precise-simulation_geomtool/.github/native-contract.json
```

After local validation, land the Geomtool contract/production change first and
the dependent mock change immediately afterward. Hosted mock qualification
intentionally checks current `geomtool/main` rather than carrying a second
contract copy in this repository.

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

To select another immutable Netgen SDK release (with its paired OCCT SDK derived
automatically):

```sh
python3 scripts/fetch_sdks.py \
  --platform linux \
  --netgen-release netgen-sdk-<source>-r1 \
  --output .deps
```

Supported keys are `windows`, `linux`, `macos-x86_64`,
`macos-arm64`, and their `-static` variants.
