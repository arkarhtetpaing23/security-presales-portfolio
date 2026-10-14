# Arkar Htet Paing — personal Linux IP-video service laboratory

I developed this personal software laboratory as part of my technical preparation for junior network and infrastructure roles in Singapore. I used it to study service commissioning, source availability, recording/playback validation, viewing permissions and controlled recovery.

## My practical work

I personally set up and ran the documented commissioning procedure on Kali Linux, reviewed its results, played both exported recordings and explained the observed service behavior. The procedure automates acceptance checks and controlled failures; my playback observations separately establish that the saved exports were usable.

| Verification stage | Actual result |
|---|---|
| Before recovery | 13/13 checks passed |
| Controlled source outage and recorder restart | 3/3 recovery checks passed |
| After recovery | The same 13/13 acceptance matrix passed again |
| Saved exports | Both decoded successfully and were personally viewed |

The repeated matrix is not 26 different features. I explained why live video alone does not establish recording/playback and why one source's outage should not interrupt the other source while the recorder remains available.

## Review the project

- [Project summary and topology](projects/ip-cctv-recording/README.md)
- [My contribution and scope](projects/ip-cctv-recording/docs/CONTRIBUTION_AND_SCOPE.md)
- [Actual results, logs and exported videos](projects/ip-cctv-recording/evidence/README.md)
- [Implementation and reproduction](projects/ip-cctv-recording/docs/IMPLEMENTATION.md)
- [File integrity manifest](SHA256SUMS.txt)

Both sources are synthetic video services and the recorder runs on the same laptop. This is a loopback software laboratory, with no physical camera, switch segmentation or commercial installation represented. It provides evidence of service verification and recovery review; unfamiliar-fault diagnosis remains a further exercise.

## Education and career preparation

I hold the NCC Education Level 4 Diploma in Computing and Level 5 Diploma in Computing (with Cyber Security), both awarded with Distinction. My academic foundations include computer networks, network security and IT project management. Educational records are supplied privately.

My [infrastructure and networking portfolio](https://github.com/arkarhtetpaing23/singapore-infrastructure-operations-labs) includes my personally executed VLAN/OSPF commissioning run and ongoing Linux recovery/monitoring practice.

## Evidence and attribution

The published operational reports and videos come from my personal Session 01. Actual results, timestamps and hashes are preserved. Source provenance and required attribution remain in the repository history and technical references. Other prepared projects are not presented as completed personal work.

Certificates, transcripts, residential address, phone numbers, CVs, passwords and private configuration files are excluded from this public repository.
