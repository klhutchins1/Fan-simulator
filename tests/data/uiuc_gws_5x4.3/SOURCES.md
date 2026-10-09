# UIUC GWS Direct-Drive 5x4.3 source files (unmodified)

Source: UIUC Propeller Database, Volume 2 (Deters 2014; Brandt, Deters, Ananda, Dantsker & Selig).
Retrieved 2026-10-09. Cite as: J.B. Brandt, R.W. Deters, G.K. Ananda, O.D. Dantsker and M.S. Selig
(retrieved 2026-10-09), *UIUC Propeller Database, Vols 1-4*, University of Illinois at
Urbana-Champaign, https://m-selig.ae.illinois.edu/props/propDB.html

The three files were extracted byte-for-byte (`unzip -p`) from the full archive:
- https://m-selig.ae.illinois.edu/props/download/UIUC-propDB.zip
  - md5 `a41e484f1fd0fb6ff80b76e27410808b`, the same value the site publishes.
  - sha256 `089b66db10391b9a3ad53aac1b95fa63d24bb7130f0dc1e6a4e7d971c5645995`.
  - Archive members are under `UIUC-propDB/volume-2/data/`, dated 2021-02-23.

Each file was also downloaded on its own from the URL below. All three were byte-identical to the
copies in the zip.

| file | URL | bytes | sha256 (as downloaded, CRLF) | sha256 if CRLF→LF |
|---|---|---|---|---|
| `gwsdd_5x4.3_geom.txt` | https://m-selig.ae.illinois.edu/props/volume-2/data/gwsdd_5x4.3_geom.txt | 416 | `68ba9f86c45abd2f00748c46d88ba4cb2258c14a693958748bc898aea0a0e9f6` | `30d66e7b6d5d202c7b1a5828a2b8a56691696c01ebef096837d57061c7f46d0b` |
| `gwsdd_5x4.3_0512rd_6047.txt` | https://m-selig.ae.illinois.edu/props/volume-2/data/gwsdd_5x4.3_0512rd_6047.txt | 715 | `11637e41bf4bb9bc372eeec37ae4789d37299388d7e5a24b648d4be398105d65` | `ab19ce454bb0b9db6ba888c995d4a8a40fbcdb4527177403eb759a7f2c4ff479` |
| `gwsdd_5x4.3_static_0493rd.txt` | https://m-selig.ae.illinois.edu/props/volume-2/data/gwsdd_5x4.3_static_0493rd.txt | 459 | `6d6c5933bd1498cb808a76964d148f75ada9bd27b44291fa82b26c90fc6b1c2d` | `c8854a5eaed80a8adf6099215e7123d0e9f7d25e4c0267a7c2ad895c978cc4a6` |

**Line endings:**
- The files use CRLF. The repo's `.gitattributes` has `* text=auto eol=lf`, which would convert
  them to LF on commit and change the first set of hashes.
- To prevent that, this folder has its own `.gitattributes` (`*.txt -text`). Running
  `git check-attr text` on these files reports `unset`.
- If they do get normalised, use the right-hand column.
- A parser should use `.split()` per line and skip the header row. That handles both CRLF and LF.

**What each file holds:**
- `geom.txt`: r/R, c/R and beta (deg) at 18 stations, 0.15 to 1.00. Diameter 5 in, 2 blades. The
  airfoil is not given; QA assumed 4 % camber.
- `0512rd_6047.txt`: J, CT, CP and eta at 6047 rpm, J 0.09 to 0.85. The QA regression point is
  J 0.571573: CT 0.055851, CP 0.049426, eta 0.645877.
- `static_0493rd.txt`: RPM, CT and CP, static, 1530 to 7897 rpm. The QA point is 7406.667 rpm:
  CT 0.148983, CP 0.074942.
