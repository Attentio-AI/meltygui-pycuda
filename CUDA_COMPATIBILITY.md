# CUDA compatibility

The support target is CUDA toolkit families **11, 12 and 13** with one installed
binding wheel per Python/platform combination. CUDA versions are not standard
wheel tags: pip and uv cannot choose a wheel by querying the GPU or toolkit.

The published `2026.1.post1` wheel is compiled against CUDA 12.1 and bundles its
cuRAND dependency. This is a build detail, not a requirement that the user's
installed toolkit also be 12.1. The driver is supplied by the system, and runtime
kernel compilation uses the user's `nvcc` and toolkit headers.

## Verified toolkit configurations

The same wheel downloaded from PyPI passes the GPU smoke test with CUDA **11.8,
12.1 and 13.0.2** on an RTX 4090 with a driver exposing CUDA API 13.2. Tests compile
and execute a kernel, perform GPU array arithmetic and reduction, exercise complex
arithmetic, and generate random numbers using cuRAND. Kernel caching is disabled
for the recorded matrix so every toolkit compiles its own kernels.

The result is in [docs/cuda-matrix.json](docs/cuda-matrix.json). These are tested
toolkit versions, not a claim that every minor release or old driver is certified.
CUDA 11.0–11.7, older driver branches, other GPU generations, and ARM/Jetson need
their own validation before being advertised as supported. A source build can
adapt bindings to local headers but cannot fix an incompatible driver or GPU.

## Repeat the GPU checks

Install the candidate wheel into a clean Python 3.12 environment, then run:

```sh
python tools/test_cuda_matrix.py \
  --cuda-root /usr/local/cuda-11.8 \
  --cuda-root /usr/local/cuda-12.1 \
  --cuda-root /usr/local/cuda-13.0 \
  --host-compiler /usr/bin/g++-11 \
  --output docs/cuda-matrix.json
```

Use toolkit paths and a host compiler supported by those toolkits on the test
machine. All three CUDA major families are required by this check. It operates
in subprocesses and does not switch the system's CUDA symlink or install drivers.

The standard hosted GitHub build verifies imports with a CUDA driver stub. It has
no GPU and does not replace this hardware test. Run this matrix before publishing
changes to the native bindings, CUDA build baseline or kernel-generation code.

References: [NVIDIA driver compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/why-cuda-compatibility.html)
and [Python wheel tags](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/).
