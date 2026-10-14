# Contribution, understanding and scope

## Personal actions established

- Ran `python3 -B lab.py commission` in the separate personal Session 01 directory on Kali Linux and supplied the actual terminal output.
- Obtained successful before/after acceptance results and all three controlled recovery results. The procedure itself generated the faults; these were guided script execution, not separately designed manual tests.
- Opened both exported MP4 files in an installed player and confirmed that both played with changing patterns.
- Explained the purpose of a synthetic source and a software recorder, why live video alone does not establish recorded playback, and why a fault in one source should not interrupt the other source while the recorder remains working.

## Personal observations and answers

Camera 1: colourful vertical bars, a diagonal line, a grey cross and small squares. Camera 2: colourful bars, a diagonal line, a checkerboard, small squares and a large grey square. Patterns and shapes changed during playback. These are candidate-reported observations; no human-player screenshot was fabricated.

My explanation: “Live video only proves that the video stream is working. It does not prove that the recorder can save the video and play it back successfully.”

My interpretation of the test: “Camera 2 continued recording normally when Camera 1 stopped. Camera 1 had a recording gap, but Camera 2 was not affected.” The checked reports establish live decoding during the outage and recorder-index availability across it; raw footage for the entire outage interval is not published here.

## Verification and source provenance

The documented procedure and source were verified before my personal commissioning run. The public results come from my personal Session 01 and are separate from earlier development verification. Publication copies preserve operational source bytes; selected logs replace the local absolute path with `<LAB_ROOT>` without changing outcomes. Required source attribution is preserved in the original history and technical references.

My Session 01 reports, source provenance, exported-file sizes and hashes were checked against the supplied terminal output. I personally executed the commissioning procedure, reviewed its results and validated both exported recordings. Fault injection and acceptance checking were automated; commercial deployment and unfamiliar-fault diagnosis are separate from this work.

## Not yet established

Physical installation, hardware compatibility, real PoE/cabling tests, long-term disk retention, production encryption, managed-switch VLANs, AutoCAD proficiency, human browser live playback and troubleshooting of unfamiliar faults are not demonstrated. Further lessons and prepared design/network materials are not represented as completed work.
