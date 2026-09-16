"""Verify the two release artifacts, package boundary, and included license notices."""
from email.parser import BytesParser
from pathlib import Path
import argparse
import os
import tarfile
import zipfile

KIND = "pycuda"
VERSION = "2026.1.post1"
NAMESPACE = "meltygui_" + KIND


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=Path("dist"))
    args = parser.parse_args()
    ref = os.environ.get("GITHUB_REF", "")
    if ref.startswith("refs/tags/"):
        assert ref == "refs/tags/v" + VERSION, "Tag must match the package version"
    wheels = list(args.directory.glob("*.whl"))
    archives = list(args.directory.glob("*.tar.gz"))
    assert len(wheels) == len(archives) == 1, "Expected exactly one wheel and one sdist"
    wheel = wheels[0]
    assert "cp312-cp312-manylinux" in wheel.name
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata = BytesParser().parsebytes(archive.read(next(n for n in names if n.endswith(".dist-info/METADATA"))))
        assert metadata["Name"].replace("_", "-") == "meltygui-" + KIND
        assert metadata["Version"] == VERSION
        assert "3.12" in metadata["Requires-Python"] and "3.13" in metadata["Requires-Python"]
        assert metadata["Home-page"] == "https://github.com/Attentio-AI/meltygui-" + KIND
        assert any(n.startswith(NAMESPACE + "/") for n in names)
        assert not any(n.startswith(KIND + "/") for n in names), "Must not overwrite upstream package"
        assert any(n.endswith(".so") for n in names)
        assert any("/licenses/LICENSE" in n for n in names)
        assert not any(n.startswith(("meltygui/", "meltygui_pro/", "meltyprivate/")) for n in names)
        if KIND == "pycuda":
            assert any("NVIDIA-CUDA-12.1-EULA" in n for n in names)
            assert any("libcurand" in n for n in names)
            assert not any(Path(n).name.startswith("libcuda.so") for n in names)
    with tarfile.open(archives[0]) as archive:
        names = archive.getnames()
        assert any(n.endswith("/UPSTREAM.json") for n in names)
        assert any(n.endswith("/LICENSE") for n in names)
        assert any("/" + NAMESPACE + "/" in n for n in names)
    print(f"Verified {metadata['Name']} {VERSION}: wheel, sdist, namespace and licenses")


if __name__ == "__main__":
    main()
