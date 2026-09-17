#!/bin/bash
set -euo pipefail
kind=$1
shift
pythons=("$@")
mkdir -p "$HOME"
export PATH=/opt/python/cp312-cp312/bin:$PATH
python -m venv /tmp/build-env
export PATH=/tmp/build-env/bin:$PATH
python -m pip install -q uv==0.11.19 auditwheel==6.4.2 patchelf==0.17.2.4
# The release build is the one compilation that is not a missing-wheel fallback.
export MELTYGUI_PYCUDA_RELEASE_BUILD=1 MELTYGUI_IMGUI_RELEASE_BUILD=1
if [ "$kind" = pycuda ]; then
  export CUDA_ROOT=/usr/local/cuda-12.1
  export PATH=$CUDA_ROOT/bin:$PATH
  export LD_LIBRARY_PATH=$CUDA_ROOT/lib64
fi
uv build --sdist --python /opt/python/cp312-cp312/bin/python /source --out-dir /output/raw
# Every wheel is built from the source archive users fall back to.
mkdir /tmp/sdist
tar -xzf /output/raw/*.tar.gz -C /tmp/sdist --strip-components=1
for tag in "${pythons[@]}"; do
  uv build --wheel --python "/opt/python/$tag-$tag/bin/python" /tmp/sdist --out-dir /output/raw
done
for wheel in /output/raw/*.whl; do
  auditwheel repair --plat manylinux_2_28_x86_64 --exclude libcuda.so.1 --wheel-dir /output "$wheel"
done
cp /output/raw/*.tar.gz /output/
: > /output/auditwheel.txt
for wheel in /output/*.whl; do
  auditwheel show "$wheel" >> /output/auditwheel.txt
done
