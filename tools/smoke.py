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
parser.add_argument('--expected-version')
parser.add_argument('--gpu', action='store_true')
args = parser.parse_args()
if args.expected_version:
    assert importlib.metadata.version('meltygui-pycuda') == args.expected_version
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
        np.testing.assert_array_equal((data + 1).get(), source * 2 + 1)
        np.testing.assert_allclose(gpuarray.sum(data).get(), (source * 2).sum())
        complex_source = source.astype(np.complex64) + 2j
        complex_data = gpuarray.to_gpu(complex_source)
        np.testing.assert_array_equal(complex_data.conj().get(), complex_source.conj())
        generator = meltygui_pycuda.curandom.XORWOWRandomNumberGenerator()
        random = generator.gen_uniform((64,), dtype=np.float32).get()
        assert random.shape == (64,) and np.all((random >= 0) & (random <= 1))
        print('GPU kernel, arrays, reduction, complex arithmetic and cuRAND passed:', cuda.Device(0).name())
    finally:
        context.pop()
        context.detach()
