# Implementation, reproduction and troubleshooting

## Tested environment and data path

The validated run used Linux x86_64 (Kali), Python 3 and pinned portable MediaMTX v1.21.2 / FFmpeg 7.0.2-static. FFmpeg was bundled in imageio-ffmpeg 0.6.0; the package version is not the executable version. See the tool reference manifest for hashes and acquisition URLs. No system package installation was required for the recorded run.

FFmpeg creates two 640 × 360 synthetic sources at 10 frames/second. They publish to separate authenticated MediaMTX endpoints. The recorder pulls those streams continuously, records available video and serves authenticated playback/export. A viewer can read/play back its authorised channels but cannot publish or access the control API.

| Endpoint | Local address/port | Purpose |
|---|---|---|
| Camera 1 | 127.20.0.11:8554 | Synthetic camera stream endpoint |
| Camera 2 | 127.20.0.12:8554 | Separate synthetic camera stream endpoint |
| Recorder | 127.30.0.10:8554 | Recorded/pulled streams for reading |
| HLS | 127.30.0.10:8888 | Authenticated live playlist/player endpoint |
| Playback | 127.30.0.10:9996 | Recording index and exported intervals |
| Control API | 127.30.0.10:9997 | Restricted recorder administration |

All services remain on loopback. Authentication does not encrypt these protocols. This configuration is an educational local demonstration, not a configuration to expose to a customer LAN or the Internet.

## Reproduce in a separate workspace

Review the source first and use a fresh folder on an authorised Linux x86_64 laptop. Keep the published `evidence` folder intact. Copy only `lab.py`, `bootstrap.py` and your tool files into that fresh run folder. Do not put new test results into the published reference directory.

The media executables are not distributed in this repository. On the original learning laptop, the already installed portable copies can be reused after comparing them with `tools/reference-manifest.json`. If a reviewer chooses to acquire them elsewhere, `bootstrap.py` downloads pinned portable tools from GitHub/PyPI, verifies package digests and writes a new local manifest. It makes network requests and writes binaries; it is optional and was not executed to prepare this release. Obtain the laptop owner's permission before downloading tools.

After choosing the tools, run in the fresh folder:

```sh
python3 -B lab.py setup
python3 -B lab.py commission
```

Setup creates unique private credentials/configuration. Commission starts the two sources and recorder, runs the acceptance matrix, stops Camera 1's publisher, checks isolation, restores it, restarts the recorder, rechecks acceptance and stops its own processes. The recorded run took approximately one to two minutes; timings can differ.

Inspect your new `evidence/verification.json`, `evidence/fault-recovery.json` and `evidence/commissioning-result.json`. Decode and personally view your own new exports. Expected stage counts are 13, 3 and 13. Preserve failures and investigate them instead of editing results.

The script tracks owned processes using PID and process start time. This prevents a recycled PID from being treated as the same process. Do not run two copies simultaneously: they use the same loopback endpoints.

## Evidence interpretation

The decoder requires real frames rather than only an HTTP success response. Final five-second exports contained 50 decoded frames each at 10 fps. An HTTP 401 from an invalid-password test is expected; receiving video without valid credentials would fail that test. A readable live stream alone does not establish recorded playback, which has separate index, export and decode checks.

The restart checker snapshots old files after shutdown finalisation, checks that their hashes remain unchanged, then waits for genuinely new files containing at least 30 decodable frames per channel. An earlier development test failed because a shutdown-finalised old fragment could be selected as a new recording. That weakness was corrected before the personal run; the failed development evidence remains local and is not relabelled as personal work.

## Troubleshooting boundaries

| Observation | Inspect/check | Meaning |
|---|---|---|
| Address already in use | Existing owned lab state and other applications on the listed ports | Stop the previously started lab in its own directory; do not kill unrelated processes |
| Missing tool | `tools/ffmpeg` and `tools/mediamtx`, architecture and reference hashes | Reuse the known local files or choose an approved acquisition route |
| Camera not ready | Source/publisher log and the matching endpoint | Check the source process and credentials; a recorder cannot save unavailable input |
| Live works but export fails | Playback index, requested interval, export log and decoder output | Live and saved-video paths are separate |
| Wrong password returns 401 | Expected-versus-observed authentication check | Expected denial is a passing access check |
| New files do not decode yet | File age, frame count and recorder/publisher logs | Wait for complete usable media within the bounded test window; keep a genuine timeout failure |

These troubleshooting suggestions were documented; they are not a claim that the candidate independently encountered and resolved each fault. Keep private configurations, passwords and keys out of shared logs.
