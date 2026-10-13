# data

Not in git: `raw/` (PDF scans, extracted frames, Middlebury folders), `demo/` (demo photo of a person), `work/`.
In git: `derived/` — measured numbers only (patch tables), no images.

Where the raw data comes from and what is known about its rights: `docs/data_sources.md`.
Expected layout on the author's machine (paths are examples; scripts take env variables):
`data/raw/Charts-PDFs/*.pdf`, `data/raw/Daylight-PDFs/`, `.../Studio-PDFs/`, `.../Night-PDFs/`, `.../Landscape-PDFs/`,
`data/raw/checker140/<camera>/wb?i?e?-{raw,jpg}.png`, `data/demo/demo_portrait.jpg`.
The originals now sit in `~/Downloads` (the PDFs total ~9 GB); moving them here is optional — leave them where they are
and point the scripts there.

`derived/film_portra400_ev0_tungsten_srgb8.csv` — Portra 400, EV 0 (1/125), tungsten, ColorChecker SG, both scanners; sRGB 8-bit median of each patch.
`derived/middlebury_wb1_i1_e3_8bit.csv` — six Middlebury cameras, tungsten 3200K, 0 stop; `*_raw` = linear data scaled to 8 bit, `*_jpg` = sRGB 8-bit.
