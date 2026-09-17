from __future__ import annotations

from os.path import dirname, join, normpath


def search_on_path(filenames):
    """Find file on system path."""
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52224

    from os import environ, pathsep
    from os.path import abspath, exists

    search_path = environ["PATH"]

    paths = search_path.split(pathsep)
    for path in paths:
        for filename in filenames:
            if exists(join(path, filename)):
                return abspath(join(path, filename))


def get_config_schema():
    from aksetup_helper import (
        BoostLibraries,
        ConfigSchema,
        IncludeDir,
        Libraries,
        LibraryDir,
        Option,
        StringListOption,
        Switch,
        make_boost_base_options,
    )

    from os import environ

    nvcc_path = search_on_path(["nvcc", "nvcc.exe"])
    if environ.get("CUDA_ROOT"):
        cuda_root_default = environ["CUDA_ROOT"]
    elif nvcc_path is None:
        print("***************************************************************")
        print("*** WARNING: nvcc not in path.")
        print("*** May need to set CUDA_INC_DIR for installation to succeed.")
        print("***************************************************************")
        cuda_root_default = None
    else:
        cuda_root_default = normpath(join(dirname(nvcc_path), ".."))

    cxxflags_default = []
    ldflags_default = []

    lib64 = "lib64"
    import sys

    if sys.platform.startswith("win"):
        # https://github.com/inducer/pycuda/issues/113
        lib64 = "lib/x64"

        import os
        if not os.environ.get("MINGW_CHOST"):
            cxxflags_default.extend(["/EHsc"])
            ldflags_default.extend(["/FORCE"])

    elif "darwin" in sys.platform:
        import glob

        root_candidates = glob.glob("/Developer/NVIDIA/CUDA-*")
        if root_candidates:
            cuda_root_default = root_candidates[-1]
            lib64 = "lib"

    default_lib_dirs = [
        "${CUDA_ROOT}/lib",
        "${CUDA_ROOT}/" + lib64,
        # https://github.com/inducer/pycuda/issues/98
        "${CUDA_ROOT}/lib/stubs",
        "${CUDA_ROOT}/%s/stubs" % lib64,
    ]

    if "darwin" in sys.platform:
        default_lib_dirs.append("/usr/local/cuda/lib")

    return ConfigSchema(
        [*make_boost_base_options(),
            Switch("USE_SHIPPED_BOOST", True, "Use included Boost library"),
            BoostLibraries("python"),
            BoostLibraries("thread"),
            Switch("CUDA_TRACE", False, "Enable CUDA API tracing"),
            Option("CUDA_ROOT", default=cuda_root_default,
                   help="Path to the CUDA toolkit"),
            Option("CUDA_PRETEND_VERSION",
                   help="Assumed CUDA version, in the form 3010 for 3.1."),
            IncludeDir("CUDA", None),
            Switch("CUDA_ENABLE_GL", True, "Enable CUDA GL interoperability"),
            Switch("CUDA_ENABLE_CURAND", True, "Enable CURAND library"),
            LibraryDir("CUDADRV", default_lib_dirs),
            Libraries("CUDADRV", ["cuda"]),
            LibraryDir("CUDART", default_lib_dirs),
            Libraries("CUDART", ["cudart"]),
            LibraryDir("CURAND", default_lib_dirs),
            Libraries("CURAND", ["curand"]),
            StringListOption("CXXFLAGS", cxxflags_default,
                             help="Any extra C++ compiler options to include"),
            StringListOption("LDFLAGS", ldflags_default,
                             help="Any extra linker options to include")]
    )


PREBUILT_WHEELS = "Linux x86-64 (glibc 2.28+), CPython 3.11, 3.12 and 3.13"
COMPILING_COMMANDS = {"bdist_wheel", "build_ext", "build", "install", "develop", "editable_wheel"}


def announce_source_build(conf):
    """Installers run this file only when no prebuilt wheel matches. Say so,
    and stop before a minute of compilation when the CUDA headers are missing.
    Release builds set MELTYGUI_PYCUDA_RELEASE_BUILD=1 to stay quiet."""
    import os
    import platform
    import sys

    if not COMPILING_COMMANDS.intersection(sys.argv) or os.environ.get("MELTYGUI_PYCUDA_RELEASE_BUILD"):
        return
    this_platform = (f"{platform.system()} {platform.machine()}, "
                     f"{platform.python_implementation()} {platform.python_version()}")
    rule = "*" * 72
    print(f"""{rule}
meltygui-pycuda: no prebuilt wheel matches this platform
  this platform:   {this_platform}
  prebuilt wheels: {PREBUILT_WHEELS}
Compiling from source instead (about a minute). This needs a C++ compiler
and an NVIDIA CUDA toolkit with nvcc on PATH, or CUDA_ROOT set.
{rule}""", file=sys.stderr, flush=True)

    if os.environ.get("MELTYGUI_PYCUDA_SKIP_PREFLIGHT"):
        return
    include_dirs = list(conf["CUDA_INC_DIR"] or [])
    if conf["CUDA_ROOT"]:
        include_dirs.append(join(conf["CUDA_ROOT"], "include"))
    for variable in ("CPATH", "CPLUS_INCLUDE_PATH"):
        include_dirs += [d for d in os.environ.get(variable, "").split(os.pathsep) if d]
    include_dirs += ["/usr/include", "/usr/local/include"]
    if not any(os.path.exists(join(d, "cuda.h")) for d in include_dirs):
        raise SystemExit(f"""{rule}
meltygui-pycuda cannot be installed here:
  no prebuilt wheel matches this platform ({this_platform}),
  and the source build cannot find the CUDA toolkit (cuda.h).
Prebuilt wheels exist for: {PREBUILT_WHEELS}.
Either use one of those Pythons, or install the CUDA toolkit and retry with
nvcc on PATH or CUDA_ROOT=/path/to/cuda (MELTYGUI_PYCUDA_SKIP_PREFLIGHT=1
skips this check). MeltyGUI's OpenGL/CPU rendering works without this package.
{rule}""")


def main():
    import sys

    from aksetup_helper import (
        ExtensionUsingNumpy,
        NumpyBuildExtCommand,
        check_git_submodules,
        get_config,
        hack_distutils,
        set_up_shipped_boost_if_requested,
        setup,
    )

    check_git_submodules()

    hack_distutils()
    conf = get_config(get_config_schema())
    announce_source_build(conf)

    EXTRA_SOURCES, EXTRA_DEFINES = set_up_shipped_boost_if_requested("pycuda", conf)

    EXTRA_DEFINES["PYGPU_PACKAGE"] = "pycuda"
    EXTRA_DEFINES["PYGPU_PYCUDA"] = "1"

    LIBRARY_DIRS = conf["BOOST_LIB_DIR"] + conf["CUDADRV_LIB_DIR"]
    LIBRARIES = (
        conf["BOOST_PYTHON_LIBNAME"]
        + conf["BOOST_THREAD_LIBNAME"]
        + conf["CUDADRV_LIBNAME"]
    )

    if not conf["CUDA_INC_DIR"] and conf["CUDA_ROOT"]:
        conf["CUDA_INC_DIR"] = [join(conf["CUDA_ROOT"], "include")]

    if conf["CUDA_TRACE"]:
        EXTRA_DEFINES["CUDAPP_TRACE_CUDA"] = 1

    if conf["CUDA_PRETEND_VERSION"]:
        EXTRA_DEFINES["CUDAPP_PRETEND_CUDA_VERSION"] = conf["CUDA_PRETEND_VERSION"]

    INCLUDE_DIRS = ["src/cpp"] + conf["BOOST_INC_DIR"]
    if conf["CUDA_INC_DIR"]:
        INCLUDE_DIRS += conf["CUDA_INC_DIR"]

    conf["USE_CUDA"] = True

    if "darwin" in sys.platform and sys.maxsize == 2147483647:
        # The Python interpreter is running in 32 bit mode on OS X
        if "-arch" not in conf["CXXFLAGS"]:
            conf["CXXFLAGS"].extend(["-arch", "i386", "-m32"])
        if "-arch" not in conf["LDFLAGS"]:
            conf["LDFLAGS"].extend(["-arch", "i386", "-m32"])

    if "darwin" in sys.platform:
        # set path to Cuda dynamic libraries,
        # as a safe substitute for DYLD_LIBRARY_PATH
        for lib_dir in conf["CUDADRV_LIB_DIR"]:
            conf["LDFLAGS"].extend(["-Xlinker", "-rpath", "-Xlinker", lib_dir])

    if conf["CUDA_ENABLE_GL"]:
        EXTRA_SOURCES.append("src/wrapper/wrap_cudagl.cpp")
        EXTRA_DEFINES["HAVE_GL"] = 1

    if conf["CUDA_ENABLE_CURAND"]:
        EXTRA_DEFINES["HAVE_CURAND"] = 1
        EXTRA_SOURCES.extend(["src/wrapper/wrap_curand.cpp"])
        LIBRARIES.extend(conf["CURAND_LIBNAME"])
        LIBRARY_DIRS.extend(conf["CURAND_LIB_DIR"])

    ver_dic = {}
    exec(
        compile(open("meltygui_pycuda/__init__.py").read(), "meltygui_pycuda/__init__.py", "exec"),
        ver_dic,
    )

    import sys

    setup(
        name="meltygui-pycuda",
        # metadata
        version="2026.1.post2",
        description="Python wrapper for Nvidia CUDA",
        long_description=open("MELTYGUI.md").read(),
        long_description_content_type="text/markdown",
        author="Andreas Kloeckner",
        author_email="inform@tiker.net",
        license="MIT",
        url="https://github.com/Attentio-AI/meltygui-pycuda",
        project_urls={
            "Source": "https://github.com/Attentio-AI/meltygui-pycuda",
            "Upstream": "https://github.com/inducer/pycuda",
        },
        classifiers=[
            "Environment :: Console",
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "Intended Audience :: Other Audience",
            "Intended Audience :: Science/Research",
            "License :: OSI Approved :: MIT License",
            "Natural Language :: English",
            "Programming Language :: C++",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Topic :: Scientific/Engineering",
            "Topic :: Scientific/Engineering :: Mathematics",
            "Topic :: Scientific/Engineering :: Physics",
            "Topic :: Scientific/Engineering :: Visualization",
        ],
        # build info
        packages=["meltygui_pycuda", "meltygui_pycuda.gl", "meltygui_pycuda.sparse", "meltygui_pycuda.compyte"],
        python_requires=">=3.11,<3.14",
        install_requires=[
            "numpy>=1.26",
            "pytools>=2011.2",
            "platformdirs>=2.2.0",
            "mako",
        ],
        test_requires=[
            "pytest>=2",
        ],
        ext_package="meltygui_pycuda",
        ext_modules=[
            ExtensionUsingNumpy(
                "_driver",
                ["src/cpp/cuda.cpp",
                    "src/cpp/bitlog.cpp",
                    "src/wrapper/wrap_cudadrv.cpp",
                    "src/wrapper/mempool.cpp",
                    *EXTRA_SOURCES],
                include_dirs=INCLUDE_DIRS,
                library_dirs=LIBRARY_DIRS,
                libraries=LIBRARIES,
                define_macros=list(EXTRA_DEFINES.items()),
                extra_compile_args=conf["CXXFLAGS"],
                extra_link_args=conf["LDFLAGS"],
            ),
            ExtensionUsingNumpy(
                "_pvt_struct",
                ["src/wrapper/_pvt_struct_v3.cpp"],
                extra_compile_args=conf["CXXFLAGS"],
                extra_link_args=conf["LDFLAGS"],
            ),
        ],
        cmdclass={"build_ext": NumpyBuildExtCommand},
        include_package_data=True,
        license_files=["LICENSE", "LICENSES/*"],
        package_data={
            "meltygui_pycuda": [
                "cuda/*.hpp",
            ]
        },
        zip_safe=False,
    )


if __name__ == "__main__":
    main()
