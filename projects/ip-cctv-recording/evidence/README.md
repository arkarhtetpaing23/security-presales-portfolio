# Evidence index — personal Session 01

The procedure was personally run on 14 October 2026 local date. JSON timestamps use UTC, so the same run is dated **13 October 2026, 18:13–18:14 UTC**. The final commissioning record is 18:14:45.280941 UTC.

| File | What it records |
|---|---|
| [Before recovery](before-recovery.json) | First 13-check acceptance matrix |
| [Fault and recovery](fault-recovery.json) | Three controlled recovery checks and observations |
| [After recovery](after-recovery.json) | Repeated 13-check matrix after the faults, final export hashes and frame counts |
| [Commissioning result](commissioning-result.json) | Overall PASS and service-stop status |
| [Stage/check table](test-results.csv) | 29 rows: 13 before, 3 recovery, 13 after |
| [Camera 1 recording index](cam01-playback-list.json) | Recorder-reported intervals with a gap around its source outage |
| [Camera 2 recording index](cam02-playback-list.json) | Recorder-reported interval spanning the Camera 1 outage |
| [Camera 1 video](videos/cam01-verified.mp4) | Actual five-second exported file, 50 decoded frames |
| [Camera 2 video](videos/cam02-verified.mp4) | Actual five-second exported file, 50 decoded frames |
| [Selected logs](../logs/) | Decoder and request logs referenced by the reports, plus the recorded command log |

The videos were personally played by the candidate. Pattern observations and explanation checks are recorded in [contribution and scope](../docs/CONTRIBUTION_AND_SCOPE.md). Human browser-live playback was not confirmed.

No PASS results from the agent's own bench are substituted for personal results. Selected logs replace the original absolute working-directory path with `<LAB_ROOT>`; generated passwords were already redacted by the commissioning procedure. Outcome fields, UTC timestamps and recorded hashes are preserved. Raw continuous recordings and private configuration files are intentionally not distributed. Recording paths inside recovery observations identify files from the original run, not additional bundled videos.

For byte checks, run `python3 -B verify_evidence.py` from the portfolio root. This is a read-only check of the included files and reports. It does not rerun the lab, prove personal authorship or independently establish all runtime claims.
