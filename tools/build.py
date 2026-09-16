"""Build the checked-out sources as a Linux x86-64 / CPython 3.12 wheel and sdist."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
KIND = "pycuda"
IMAGE = "quay.io/pypa/manylinux_2_28_x86_64@sha256:531d7aa844bbb0c131d4ab011d3db741c4abc8d498cd5ccc86121046f62303b4"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--cuda-root", type=Path)
    parser.add_argument("--sudo-docker", action="store_true")
    args = parser.parse_args()
    if KIND == "pycuda" and (not args.cuda_root or not (args.cuda_root / "include/cuda.h").exists()):
        parser.error("PyCUDA needs --cuda-root pointing at a CUDA 12.1 toolkit")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.glob("*.whl")) or any(output.glob("*.tar.gz")):
        parser.error("Use an output directory without existing release artifacts")
    docker = ["sudo", "-n", "docker"] if args.sudo_docker else ["docker"]
    with tempfile.TemporaryDirectory(prefix="meltygui-native-") as work:
        source = Path(work) / "source"
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(
            ".git", ".venv", "__pycache__", ".pytest_cache", "*.egg-info", "dist", "build", "*.so", "siteconf.py"))
        command = [*docker, "run", "--rm", "--platform", "linux/amd64",
                   "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp/build-home",
                   "-v", f"{source}:/source", "-v", f"{output}:/output",
                   "-v", f"{ROOT / 'tools'}:/tools:ro"]
        if args.cuda_root:
            command += ["-v", f"{args.cuda_root.resolve()}:/usr/local/cuda-12.1:ro"]
        subprocess.run([*command, IMAGE, "bash", "/tools/build_in_container.sh", KIND], check=True)
    artifacts = [*output.glob("*.whl"), *output.glob("*.tar.gz")]
    revision = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    receipt = {"kind": KIND, "upstream": json.loads((ROOT / "UPSTREAM.json").read_text()),
               "build_image": IMAGE, "python": "CPython 3.12", "target": "manylinux_2_28_x86_64",
               "revision": revision.stdout.strip() or None,
               "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}}
    (output / "build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
