"""Extract the scan frames of one page of a Color Precision comparison PDF, in reading order.

The PDFs (Pages -> Quartz) keep every scan as an embedded image with an Apple 'Display' ICC profile,
so the pixels come out untouched. Usage:
    python3 tools/film_measure/extract_pdfs.py "Charts Frontier Scans.pdf" 2 out_dir [prefix]
Writes <prefix>_<k>.png (k = 1.. in reading order: top-to-bottom, left-to-right, title cell skipped)
and display.icc. EV order of the frames comes from the page label (e.g. -3,-1,0,+1,+2,+3,+4); verify it
against the shutter speed written on the white board in each frame (Charts, Portra 400: 1/1000, 1/250,
1/125, 1/60, 1/30, 1/15, 1/8 = EV -3,-1,0,+1,+2,+3,+4). Frontier pages may carry one extra frame.
Needs: poppler-utils (pdfimages), pypdf.
"""
import glob, os, shutil, subprocess, sys, tempfile
import pypdf
from pypdf.generic import ContentStream

def frame_order(pdf, page):
    r = pypdf.PdfReader(pdf); pg = r.pages[page - 1]; xo = pg['/Resources']['/XObject']
    cs = ContentStream(pg.get_contents(), r); stack = []; cur = [1, 0, 0, 1, 0, 0]; out = []
    for ops, op in cs.operations:
        if op == b'q': stack.append(cur[:])
        elif op == b'Q': cur = stack.pop() if stack else cur
        elif op == b'cm':
            a, b, c, d, e, f = [float(x) for x in ops]; A = cur
            cur = [a*A[0]+b*A[2], a*A[1]+b*A[3], c*A[0]+d*A[2], c*A[1]+d*A[3], e*A[0]+f*A[2]+A[4], e*A[1]+f*A[3]+A[5]]
        elif op == b'Do':
            o = xo[ops[0]].get_object()
            if o.get('/Subtype') == '/Image' and o.get('/Width', 0) > 2200 and o.get('/Width') != o.get('/Height'):
                out.append((ops[0], cur[4], cur[5]))      # name, x, y (PDF origin = bottom-left)
    return r, pg, out

def main(pdf, page, out_dir, prefix='frame'):
    os.makedirs(out_dir, exist_ok=True)
    r, pg, order = frame_order(pdf, page)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['pdfimages', '-f', str(page), '-l', str(page), '-png', pdf, os.path.join(tmp, 'p')], check=True)
        files = sorted(f for f in glob.glob(os.path.join(tmp, 'p-*.png')))
        from PIL import Image
        photos = [f for f in files if Image.open(f).width > 2200 and Image.open(f).width != Image.open(f).height]
        assert len(photos) == len(order), (len(photos), len(order))
        # draw order == pdfimages order; reading order = top-to-bottom (y desc), then left-to-right (x asc)
        idx = sorted(range(len(order)), key=lambda i: (-round(order[i][2] / 50), order[i][1]))
        for k, i in enumerate(idx, 1):
            shutil.move(photos[i], os.path.join(out_dir, f'{prefix}_{k}.png'))
    icc = pg['/Resources']['/XObject'][order[0][0]].get_object()['/ColorSpace'][1].get_object().get_data()
    open(os.path.join(out_dir, 'display.icc'), 'wb').write(icc)
    print(f'{len(order)} frames -> {out_dir}')

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3], *(sys.argv[4:5] or []))
