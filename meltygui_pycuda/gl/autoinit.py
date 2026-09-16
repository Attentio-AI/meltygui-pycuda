from __future__ import annotations

import atexit

import meltygui_pycuda.driver as cuda
import meltygui_pycuda.gl as cudagl


cuda.init()
assert cuda.Device.count() >= 1

from meltygui_pycuda.tools import make_default_context


context = make_default_context(lambda dev: cudagl.make_context(dev))
device = context.get_device()

atexit.register(context.pop)
