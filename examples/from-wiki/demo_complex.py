#!python
from __future__ import annotations

import numpy

from meltygui_pycuda import gpuarray


a = (numpy.random.randn(400)
        +1j*numpy.random.randn(400)).astype(numpy.complex64)
b = (numpy.random.randn(400)
        +1j*numpy.random.randn(400)).astype(numpy.complex64)

a_gpu = gpuarray.to_gpu(a)
b_gpu = gpuarray.to_gpu(b)

from meltygui_pycuda.elementwise import ElementwiseKernel


complex_mul = ElementwiseKernel(
        "meltygui_pycuda::complex<float> *x, meltygui_pycuda::complex<float> *y, meltygui_pycuda::complex<float> *z",
        "z[i] = x[i] * y[i]",
        "complex_mul",
        preamble="#include <meltygui_pycuda-complex.hpp>",)

c_gpu = gpuarray.empty_like(a_gpu)
complex_mul(a_gpu, b_gpu, c_gpu)

import numpy.linalg as la


error = la.norm(c_gpu.get() - (a*b))
print(error)
assert error < 1e-5
