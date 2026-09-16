"""Check installed imports; --gpu also compiles and runs a CUDA kernel."""
import argparse
import importlib.metadata
import importlib.util

import meltygui_pycuda.driver as cuda
import meltygui_pycuda.compiler
import meltygui_pycuda.gpuarray
import meltygui_pycuda.gl
import meltygui_pycuda.curandom

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--gpu', action='store_true')
args = parser.parse_args()
assert importlib.metadata.version('meltygui-pycuda') == '2026.1.post1'
assert importlib.util.find_spec('pycuda') is None
assert cuda.get_version() == (12, 1, 0)
assert hasattr(meltygui_pycuda.gl, 'RegisteredBuffer')
print('Installed PyCUDA wheel: driver, compiler, GPU arrays, OpenGL and cuRAND imports passed')
if args.gpu:
    import numpy as np
    from meltygui_pycuda.compiler import SourceModule
    from meltygui_pycuda import gpuarray

    cuda.init()
    context = cuda.Device(0).make_context()
    try:
        source = np.arange(64, dtype=np.float32)
        data = gpuarray.to_gpu(source)
        module = SourceModule('''
        __global__ void twice(float *values) {
            const int i = threadIdx.x;
            values[i] *= 2.0f;
        }
        ''', cache_dir=False)
        module.get_function('twice')(data, block=(64, 1, 1))
        np.testing.assert_array_equal(data.get(), source * 2)
        random = meltygui_pycuda.curandom.rand((64,), dtype=np.float32).get()
        assert random.shape == (64,) and np.all((random >= 0) & (random <= 1))
        print('GPU kernel compilation, execution, round-trip and cuRAND passed:', cuda.Device(0).name())
    finally:
        context.pop()
        context.detach()
