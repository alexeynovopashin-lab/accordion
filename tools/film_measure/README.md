# film_measure — how the film / scanner / digital numbers were made

Pipeline (each step is one script, run from the repo root; inputs live in `data/raw/`, git-ignored):

1. `extract_pdfs.py` — frames out of the Color Precision PDFs (untouched pixels + ICC).
2. `find_plates.py`, `holes.py`, `sg_lattice.py` — find the ColorChecker SG, fit the 14x10 patch lattice
   (rotation, pitch; black patches restored from the lattice), sample the central part of every patch.
   `python3 tools/film_measure/sg_lattice.py` writes `rgb_*.npy` and an overlay `ov_*.png` — look at the overlay.
3. `compare_scanners.py` — Frontier vs Noritsu, patch by patch (dE2000, grey-ramp matching, hue families).
4. `film_vs_digital.py` — the same film frame vs Middlebury cameras (RAW is linear, JPG is sRGB).

`colorlib.py` — sRGB -> Lab D50 and CIEDE2000 (checked against the Sharma test pair: 2.0425).
Needs: Python 3, numpy, scipy, opencv-python, Pillow, pypdf, poppler-utils. Results: `docs/experiments/`.
Environment variables: `CHARTS_EXTRACT` (folder with extracted frames + `charts.icc`), `MIDDLEBURY` (checker140).
Status: ran on 2026-10-13 on the author's data; `extract_pdfs.py` verified end to end on Charts page 2 (frame 3 in reading order = EV 0, bit-identical to the frames used in the tests).
