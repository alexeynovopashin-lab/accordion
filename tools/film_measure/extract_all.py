"""Extract every film page of both Charts PDFs and write a manifest.

    python3 tools/film_measure/extract_all.py <Charts-PDFs dir> <out dir>
Per page: frames in reading order -> <out>/<scanner>/p<NN>/f<k>.png; manifest.csv:
scanner, page, film (from the page title), k, file, width, height.
Frames are NOT yet matched to EV: the title lists EV -3,-1,0,+1,+2,+3,+4 (7 values), check against the board in the frame.
Pages that are not film pages (no big images, e.g. the lighting diagram) are skipped and noted in the log.
Needs poppler-utils (pdfimages), pypdf, Pillow. The PDFs are 1-1.5 GB; optional 3rd argument = time budget in seconds, the run is resumable (pages already extracted are skipped).
"""
import csv, os, re, sys, glob, subprocess
import pypdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_pdfs

PDFS = {'frontier': 'Charts Frontier Scans.pdf', 'noritsu': 'Charts Norritsu Scans.pdf'}

def title(txt):
    t = re.sub(r'\s+', ' ', txt.replace(' ', ' ')).strip()
    m = re.search(r'((?:Portra|Ektar|Gold|UltraMax|ColorPlus|Pro|Fuji|Kodak)[^,]*?)\s+E[Vv]\s', t)
    return (m.group(1) if m else t[:60]).strip()

def main(src, out, budget=None):
    import time; t0=time.time()
    rows, log = [], []
    for scanner, name in PDFS.items():
        pdf = os.path.join(src, name); n = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout).group(1))
        for page in range(1, n + 1):
            film = title(subprocess.run(['pdftotext', '-f', str(page), '-l', str(page), pdf, '-'], capture_output=True, text=True).stdout)
            d = os.path.join(out, scanner, f'p{page:02d}')
            try:
                if not glob.glob(os.path.join(d, 'f_*.png')):
                    if budget and time.time() - t0 > budget: print('budget reached, rerun to resume'); return
                    extract_pdfs.main(pdf, page, d, 'f')
            except Exception as e:
                log.append(f'{scanner} p{page} "{film}": skipped ({type(e).__name__}: {e})'); print(log[-1], flush=True); continue
            from PIL import Image
            for f in sorted(glob.glob(os.path.join(d, 'f_*.png')), key=lambda s: int(re.findall(r'_(\d+)\.png', s)[0])):
                k = int(re.findall(r'_(\d+)\.png', f)[0]); w, h = Image.open(f).size
                rows.append([scanner, page, film, k, os.path.relpath(f, out), w, h])
            print(f'{scanner} p{page} {film}', flush=True)
    with open(os.path.join(out, 'manifest.csv'), 'w', newline='') as fh:
        csv.writer(fh).writerows([['scanner', 'page', 'film', 'k', 'file', 'width', 'height']] + rows)
    open(os.path.join(out, 'log.txt'), 'w').write('\n'.join(log))
    print('done', len(rows), 'frames')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else None)
