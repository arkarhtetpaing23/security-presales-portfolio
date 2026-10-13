#!/usr/bin/env python3
"""Fetch portable Linux x86_64 lab tools; no system installation."""
import hashlib
import io
import json
import platform
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / 'tools'

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Arkar-CCTV-Lab1/1.0'})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()

def main():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'AMD64'):
        raise SystemExit('This portable bootstrap supports Linux x86_64 only.')
    TOOLS.mkdir(exist_ok=True)
    release = json.loads(fetch('https://api.github.com/repos/bluenviron/mediamtx/releases/tags/v1.21.2'))
    asset = next(a for a in release['assets'] if a['name'].endswith('_linux_amd64.tar.gz'))
    archive = fetch(asset['browser_download_url'])
    digest = hashlib.sha256(archive).hexdigest()
    upstream_digest = asset.get('digest')
    if upstream_digest and upstream_digest != 'sha256:' + digest:
        raise SystemExit('MediaMTX archive SHA256 differs from GitHub asset metadata.')
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
        for name in ('mediamtx', 'mediamtx.yml', 'LICENSE'):
            member = next(m for m in tar.getmembers() if Path(m.name).name == name and m.isfile())
            target = TOOLS / ('mediamtx-default.yml' if name == 'mediamtx.yml' else 'MEDIAMTX-LICENSE' if name == 'LICENSE' else name)
            target.write_bytes(tar.extractfile(member).read())
    (TOOLS / 'mediamtx').chmod(0o755)
    package = json.loads(fetch('https://pypi.org/pypi/imageio-ffmpeg/0.6.0/json'))
    wheel = next(a for a in package['urls'] if 'manylinux' in a['filename'] and 'x86_64' in a['filename'])
    wheel_data = fetch(wheel['url'])
    wheel_sha = hashlib.sha256(wheel_data).hexdigest()
    if wheel_sha != wheel['digests']['sha256']:
        raise SystemExit('FFmpeg wheel SHA256 differs from PyPI metadata.')
    with zipfile.ZipFile(io.BytesIO(wheel_data)) as z:
        name = next(n for n in z.namelist() if '/binaries/ffmpeg-' in n and not n.endswith('/'))
        (TOOLS / 'ffmpeg').write_bytes(z.read(name))
        for n in z.namelist():
            if 'license' in n.lower() and not n.endswith('/'):
                (TOOLS / ('IMAGEIO-' + Path(n).name)).write_bytes(z.read(n))
    (TOOLS / 'ffmpeg').chmod(0o755)
    manifest = {'mediamtx': {'version': release['tag_name'], 'url': asset['browser_download_url'], 'archive_sha256': digest, 'github_asset_digest': upstream_digest},
                'ffmpeg_distribution': {'package': 'imageio-ffmpeg', 'version': '0.6.0', 'url': wheel['url'], 'wheel_sha256': wheel_sha},
                'binary_sha256': {n: hashlib.sha256((TOOLS/n).read_bytes()).hexdigest() for n in ('mediamtx','ffmpeg')}}
    (TOOLS / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Downloaded portable MediaMTX', release['tag_name'])
    print('Downloaded bundled FFmpeg from imageio-ffmpeg 0.6.0')
    print('Verified package digests; recorded binary hashes in tools/manifest.json')

if __name__ == '__main__':
    main()
