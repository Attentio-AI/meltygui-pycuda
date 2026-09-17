# meltygui-pycuda

Namespaced pycuda bindings maintained for MeltyGUI, based on the upstream source
recorded in [UPSTREAM.json](UPSTREAM.json). Original authorship and licenses are
preserved. This repository contains the binding source and its release tooling.

```sh
uv pip install meltygui-pycuda
```

```python
import meltygui_pycuda
```

The current release is **2026.1.post2**, with wheels for Linux x86-64 (glibc 2.28
or newer) on CPython 3.11, 3.12 and 3.13. It installs `meltygui_pycuda` without
overwriting the upstream `pycuda` package.

### When no wheel matches

On any other platform or Python, pip and uv fall back to the source archive
without saying that no wheel matched. The build prints a banner naming your
platform and the prebuilt targets (installers show it with `-v`, or when the
build fails), and stops at once with a short message if the CUDA headers are
missing instead of compiling for a minute first. A source build needs a C++
compiler and a CUDA toolkit: put `nvcc` on PATH or set `CUDA_ROOT`. It takes
about a minute and links the toolkit's own cuRAND rather than a bundled copy.
uv ignores the upper Python bound, so on a newer Python it also builds from
source; pip refuses instead. Pass `--only-binary meltygui-pycuda` to make a
missing wheel an error rather than a compilation.

OpenGL interoperability and cuRAND are enabled. Wheels bundle cuRAND with its
NVIDIA CUDA 12.1 license; the driver and nvcc are not bundled. Runtime kernel
compilation still requires a compatible CUDA toolkit and NVIDIA driver.

## Build

Docker is required. The manylinux image and Python build dependencies are pinned.
The wheel is built from the generated source archive, which is also published
for local compilation when a matching wheel is unavailable.

```sh
python3 tools/build.py --cuda-root /usr/local/cuda-12.1
python3 tools/verify.py dist
uvx --from twine==7.0.0 twine check --strict dist/*.whl dist/*.tar.gz
```

Use `--sudo-docker` if Docker requires sudo. Source builds require a C++ compiler and a CUDA toolkit with nvcc on PATH.

## Publish

Pushes to `main` and pull requests build and test without uploading. A `v*` tag
or a manual run with `publish=true` publishes the verified wheel and source
archive through PyPI trusted publishing. Published versions cannot be replaced.

Configure a pending GitHub publisher at https://pypi.org/manage/account/publishing/:

| Field | Value |
| --- | --- |
| PyPI project | `meltygui-pycuda` |
| Owner | `Attentio-AI` |
| Repository | `meltygui-pycuda` |
| Workflow | `release.yml` |
| Environment | `pypi` |

Then, after the main-branch build passes, create and push `v2026.1.post2`.
No API token belongs in this repository.

## Licenses and changes

See [LICENSE](LICENSE), [LICENSES](LICENSES), and [MELTYGUI.md](MELTYGUI.md).
The primary changes are the Python namespace, pinned build dependencies,
Python 3.12 support, and OpenGL/cuRAND enabled by default.
