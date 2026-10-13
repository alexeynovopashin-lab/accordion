"""Build the browser prototype.

Source of truth: prototype/complement.html (placeholder __DEMO_IMG__ for the demo photo).
Output (git-ignored): prototype/build/complement_built.html  - what gets published as the artifact,
                      prototype/build/test_built.html        - same + window.__t hooks for tests.
Demo photo: data/demo/demo_portrait.jpg (git-ignored: a private photo of a person).
Run:  python3 prototype/build.py
"""
import base64, io, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
demo = os.path.join(ROOT, "data", "demo", "demo_portrait.jpg")
if os.path.exists(demo):
    im = Image.open(demo).convert("RGB"); s = 1400 / max(im.size)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=90); src = "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
else:
    print("no demo photo at", demo, "- building without demo image", file=sys.stderr)
    src = "data:image/gif;base64,R0lGODlhAQABAAAAACw="   # 1x1 stub
out = open(os.path.join(HERE, "complement.html"), encoding="utf-8").read().replace("__DEMO_IMG__", src)
os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
open(os.path.join(HERE, "build", "complement_built.html"), "w", encoding="utf-8").write(out)
i = out.rfind("})();")
hooks = "window.__t={P,prepAll,normLch,transformHue,get NM(){return NM},get PINS(){return PINS}};\n"
open(os.path.join(HERE, "build", "test_built.html"), "w", encoding="utf-8").write(out[:i] + hooks + out[i:])
print("built", os.path.join(HERE, "build"))
