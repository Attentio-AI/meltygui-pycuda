"""Run one installed wheel against CUDA 11, 12 and 13 on a real GPU."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cuda-root', type=Path, action='append', required=True)
    parser.add_argument('--host-compiler', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    toolkits = []
    for root in args.cuda_root:
        root = root.resolve()
        version = subprocess.check_output([str(root / 'bin/nvcc'), '--version'], text=True)
        match = re.search(r'release (\d+)\.(\d+)', version)
        if not match:
            parser.error(f'Cannot identify toolkit at {root}')
        toolkits.append((root, int(match[1]), match[0].removeprefix('release ')))
    if {major for _, major, _ in toolkits} != {11, 12, 13}:
        parser.error('Provide toolkits covering all three majors: 11, 12 and 13')

    import meltygui_pycuda.driver as cuda
    cuda.init()
    report = {
        'tested_at': datetime.now(timezone.utc).isoformat(),
        'package_version': importlib.metadata.version('meltygui-pycuda'),
        'binding_build_toolkit': list(cuda.get_version()),
        'driver_api_version': cuda.get_driver_version(),
        'gpu': cuda.Device(0).name(),
        'scope': 'Toolkit matrix on one installed driver; not an older-driver certification',
        'results': [],
    }
    script = Path(__file__).with_name('smoke.py')
    for root, major, version in toolkits:
        env = os.environ.copy()
        env['PATH'] = str(root / 'bin') + os.pathsep + env.get('PATH', '')
        env['CUDA_ROOT'] = str(root)
        env['PYCUDA_DISABLE_CACHE'] = '1'
        if args.host_compiler:
            env['PYCUDA_DEFAULT_NVCC_FLAGS'] = '-ccbin=' + str(args.host_compiler.resolve())
        result = subprocess.run([sys.executable, '-I', str(script), '--gpu'],
                                env=env, capture_output=True, text=True)
        report['results'].append({'toolkit': version, 'passed': result.returncode == 0,
                                  'stdout': result.stdout, 'stderr': result.stderr})
        print(f'CUDA {version}: {"PASS" if result.returncode == 0 else "FAIL"}', flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    if not all(result['passed'] for result in report['results']):
        raise SystemExit('CUDA compatibility checks failed; see ' + str(args.output))


if __name__ == '__main__':
    main()
