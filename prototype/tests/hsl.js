// «Цвета» (HSL by sectors) checks. Run from prototype/build:  node ../tests/hsl.js
// (а) skin core and neutral core do not change at extreme sliders (outputs bit-identical, i.e. ΔE = 0)
// (б) a sector with a sample changes what is like the sample and leaves what is unlike it bit-identical
// (в) no hue / chroma / lightness folds of the stage at extreme sliders (short fold.js)
// (г) the exported .cube (sRGB 65), applied to the frame, against the exact per-pixel render (±1 level on ≥ 99.95% of pixels)
// (д) the plate in the real page: place and default, sample by click, mask, undo/redo, reset all, LUT comment line
// (е) lips (measurement, no pass/fail): share of hand-outlined lip pixels with red-sector weight > 0.1 —
//     standard sector, and sector with a sample taken on another red object (chart red patch, hair)
// BREAK=1 removes the fold guard from the page: (в) must turn red.
const { chromium } = require('playwright');
const fs = require('fs');
const NEW = process.cwd()+'/complement_built.html', TEST = process.cwd()+'/test_built.html';
const launch = () => chromium.launch({ ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
let fails = 0; const ok = (name, cond, info) => { console.log((cond ? 'PASS ' : 'FAIL ')+name+(info ? '  '+info : '')); if (!cond) fails++; };
const mock = () => { window.__saved = []; window.claude = { use: async () => ({ save: async ({ filename, data }) => {
  const b = new Uint8Array(await data.arrayBuffer()); window.__saved.push([filename, Array.from(b)]); } }) }; };
// places on the demo portrait (1717×2576), as fractions of the frame
const FW = 1717, FH = 2576;
const SPOT = { redPatch:[435/FW, 1897/FH], greenPatch:[570/FW, 1897/FH], hair:[650/FW, 1000/FH] };
// lips outlined by hand on the full-size demo (pixels); the outline takes 1–3 px of skin at the lower left edge
const LIPS = [[891.7,885],[906.7,883.3],[930,884],[960,888.3],[986.7,896],[1006.7,898.3],[1033.3,903.3],[1040,910],[1020,920],
  [1006.7,930],[986.7,941.7],[966.7,946],[946.7,943.3],[926.7,933.3],[913.3,920],[903.3,900]].map(([x,y]) => [x/FW, y/FH]);

(async () => {
  const b = await launch();
  let html = fs.readFileSync(TEST, 'utf8');
  if (process.env.BREAK){
    const g = "  if (!amt.some(Boolean)) return amt.slice();\n";
    if (!html.includes(g)) { console.log('BREAK: guard string not found'); process.exit(2); }
    html = html.replace(g, "  return amt.slice();\n"); console.log('BREAK: fold guard removed');
  }
  const tmp = process.cwd()+'/hsl_test_tmp.html'; fs.writeFileSync(tmp, html);
  const p = await b.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://'+tmp); await p.waitForTimeout(2500);
  const r = await p.evaluate(({ SPOT, LIPS }) => {
    const T = window.__t, P = T.P, res = {};
    const W = T.srcData.width, H = T.srcData.height, d = T.srcData.data;
    const Z = { h:0, s:0, l:0, ref:null, reach:1 };
    const mk = f => Object.freeze({ sec:Object.freeze(Array.from({length:8}, (_,i) => Object.freeze({ ...Z, ...f(i) }))) });
    const rgb = i => [d[i*4]/255, d[i*4+1]/255, d[i*4+2]/255];
    const run = (hsl, idx) => { P.hsl = hsl; T.prepAll(); return idx.map(i => T.xf(...rgb(i), 'srgb')); };
    const same = (a, b) => a[0]===b[0] && a[1]===b[1] && a[2]===b[2];
    // CIEDE2000 on Lab D50
    const de00 = (x, y) => {
      const [L1,a1,b1] = x, [L2,a2,b2] = y, R = Math.PI/180, C1 = Math.hypot(a1,b1), C2 = Math.hypot(a2,b2), Cm = (C1+C2)/2;
      const G = 0.5*(1-Math.sqrt(Math.pow(Cm,7)/(Math.pow(Cm,7)+Math.pow(25,7)))), A1 = a1*(1+G), A2 = a2*(1+G);
      const c1 = Math.hypot(A1,b1), c2 = Math.hypot(A2,b2), h1 = (Math.atan2(b1,A1)/R+360)%360, h2 = (Math.atan2(b2,A2)/R+360)%360;
      const dL = L2-L1, dC = c2-c1; let dh = c1*c2 ? h2-h1 : 0; if (dh > 180) dh -= 360; if (dh < -180) dh += 360;
      const dH = 2*Math.sqrt(c1*c2)*Math.sin(dh*R/2), Lm = (L1+L2)/2, cm = (c1+c2)/2;
      let hm = h1+h2; if (c1*c2){ if (Math.abs(h1-h2) > 180) hm += hm < 360 ? 360 : -360; hm /= 2; }
      const Tt = 1-0.17*Math.cos((hm-30)*R)+0.24*Math.cos(2*hm*R)+0.32*Math.cos((3*hm+6)*R)-0.2*Math.cos((4*hm-63)*R);
      const SL = 1+0.015*(Lm-50)*(Lm-50)/Math.sqrt(20+(Lm-50)*(Lm-50)), SC = 1+0.045*cm, SH = 1+0.015*cm*Tt;
      const RT = -2*Math.sqrt(Math.pow(cm,7)/(Math.pow(cm,7)+Math.pow(25,7)))*Math.sin(60*Math.exp(-Math.pow((hm-275)/25,2))*R);
      return Math.sqrt(Math.pow(dL/SL,2)+Math.pow(dC/SC,2)+Math.pow(dH/SH,2)+RT*(dC/SC)*(dH/SH));
    };
    const lab = o => T.labD50(o.map(T.toLin));
    const med = a => { const s = Float64Array.from(a).sort(); return s.length ? s[Math.floor(s.length/2)] : NaN; };
    const box = (f, r) => { const cx = Math.round(f[0]*W), cy = Math.round(f[1]*H), o = []; for (let y=cy-r;y<=cy+r;y++) for (let x=cx-r;x<=cx+r;x++) o.push(y*W+x); return o; };
    const inPoly = (x, y, poly) => { let c = false; for (let i=0, j=poly.length-1; i<poly.length; j=i++){ const [xi,yi] = poly[i], [xj,yj] = poly[j]; if ((yi>y) !== (yj>y) && x < (xj-xi)*(y-yi)/(yj-yi)+xi) c = !c; } return c; };
    const lips = []; { const pp = LIPS.map(([x,y]) => [x*W, y*H]); for (let y=0;y<H;y++) for (let x=0;x<W;x++) if (inPoly(x+0.5, y+0.5, pp)) lips.push(y*W+x); }
    const every = []; for (let i=0;i<W*H;i+=5) every.push(i);
    const qOf = i => T.xfPre(...rgb(i), 'srgb');
    const def = T.defaultHsl();
    const base = run(def, every);

    // (а) skin core and neutral core
    const skinIdx = Array.from(T.cloudOf('skin'));
    T.prepAll();
    const skinCore = skinIdx.filter(i => { const q = qOf(i); return q[1] > 1e-5 && T.hsSkinW(...q) >= 1-1e-12; });
    const neutCore = every.filter(i => qOf(i)[1] <= P.neutral);
    const skinBase = run(def, skinCore);
    const nb = new Map(every.map((i,k) => [i, base[k]]));
    const lipsRef = Object.freeze({ L:0.62, C:0.07, h:30 });
    res.a = [];
    for (const [name, hsl] of [['all +30/+100/+100', mk(() => ({ h:30, s:100, l:100 }))], ['all −30/−100/−100', mk(() => ({ h:-30, s:-100, l:-100 }))],
                               ['red+orange sample near skin, extreme', mk(i => i===0 ? { h:30, s:100, l:-100, ref:lipsRef, reach:2 } : i===1 ? { h:-30, s:-100, l:100, ref:Object.freeze({ L:0.7, C:0.07, h:50 }), reach:2 } : {})]]){
      const s1 = run(hsl, skinCore), n1 = run(hsl, neutCore);
      const sd = s1.filter((o,k) => !same(o, skinBase[k])).length, nd = n1.filter((o,k) => !same(o, nb.get(neutCore[k]))).length;
      res.a.push([name, skinCore.length, sd, neutCore.length, nd]);
    }

    // (б) sample on the chart red patch: like it → changed, unlike it → bit-identical
    P.hsl = def; T.prepAll(); T.HUI.sel = 0;
    const rp = box(SPOT.redPatch, 0)[0]; T.hslTakeRef(rp%W, Math.floor(rp/W));
    const ref = P.hsl.sec[0].ref;
    const withRef = s => Object.freeze({ sec:Object.freeze(P.hsl.sec.map((x,i) => i===0 ? Object.freeze({ ...x, ...s }) : x)) });
    const hslB = withRef({ h:20, s:50, l:-50 });
    const ed = run(hslB, every);
    let zero = 0, zeroDiff = 0; const strong = [];
    every.forEach((i,k) => { const w = T.hsWeightAt(qOf(i), 0); if (w === 0){ zero++; if (!same(ed[k], base[k])) zeroDiff++; } else if (w >= 0.9) strong.push(de00(lab(ed[k]), lab(base[k]))); });
    const regionDE = f => { const idx = box(f, 12), a = run(def, idx), z = run(hslB, idx); return a.map((o,k) => de00(lab(o), lab(z[k]))); };
    const redDE = regionDE(SPOT.redPatch), greenDE = regionDE(SPOT.greenPatch);
    res.b = { ref, zero, zeroDiff, strongN:strong.length, strongMed:med(strong), redMed:med(redDE), greenMax:Math.max(...greenDE) };

    // (в) folds of the stage at extreme sliders (stage alone, grid off the guard's grid)
    res.c = [];
    for (const [name, hsl] of [['red+30 orange−30', mk(i => i===0 ? { h:30 } : i===1 ? { h:-30 } : {})], ['alternating extremes', mk(i => i%2 ? { h:30, s:100, l:-100 } : { h:-30, s:-100, l:100 })],
                               ['red sample reach 0.5', mk(i => i===0 ? { h:30, s:-100, l:100, ref:lipsRef, reach:0.5 } : {})]]){
      P.hsl = hsl; T.prepAll(); let hf = 0, cf = 0, lf = 0;
      for (let L=0.15; L<=0.97; L+=0.035) for (let C=0.013; C<=0.3; C+=0.011){ let pv = null; for (let h=0; h<=360; h+=0.5){ const v = T.hslStage(L,C,h)[2]; if (pv!==null && ((v-pv+540)%360)-180 < -1e-6) hf++; pv = v; } }
      for (let L=0.3; L<=0.95; L+=0.07) for (let h=1; h<360; h+=4){ let pv = -1; for (let C=0.001; C<=0.34; C+=0.002){ const v = T.hslStage(L,C,h)[1]; if (v < pv-1e-9) cf++; pv = v; } }
      for (let C=0.015; C<=0.3; C+=0.025) for (let h=2; h<360; h+=4){ let pv = -1; for (let L=0.02; L<=1; L+=0.005){ const v = T.hslStage(L,C,h)[0]; if (v < pv-1e-9) lf++; pv = v; } }
      res.c.push([name, hf, cf, lf]);
    }

    // (г) .cube sRGB 65 applied to the frame (trilinear, as any program does) vs the exact render, in 8-bit levels
    const cubeVsRender = hsl => {
      P.hsl = hsl; T.prepAll();
      const txt = T.cubeText(65, 'srgb'), lines = txt.split('\n').filter(l => /^[0-9.\-]+ [0-9.\-]+ [0-9.\-]+$/.test(l));
      const N = 65, lut = new Float32Array(N*N*N*3); lines.forEach((l,k) => { const v = l.split(' ').map(Number); lut[k*3]=v[0]; lut[k*3+1]=v[1]; lut[k*3+2]=v[2]; });
      const src = new Uint8ClampedArray(every.length*4); every.forEach((i,k) => { for (let c=0;c<4;c++) src[k*4+c] = d[i*4+c]; });
      const dst = new Uint8ClampedArray(src.length); T.applyLUT(src, dst, lut, N);
      let mx = 0, over = 0;
      every.forEach((i,k) => { const o = T.xf(...rgb(i), 'srgb'); let m = 0; for (let c=0;c<3;c++) m = Math.max(m, Math.abs(dst[k*4+c] - Math.round(o[c]*255))); mx = Math.max(mx, m); if (m > 1) over++; });
      return { lines:lines.length, hasHsl:txt.includes('# hsl'), max:mx, over, n:every.length };
    };
    res.d = { off:cubeVsRender(def), on:cubeVsRender(hslB) };

    // (е) lips
    const share = (hsl, idx, thr) => { P.hsl = hsl; T.prepAll(); return idx.filter(i => T.hsWeightAt(qOf(i), 0) > thr).length/idx.length; };
    const std = mk(i => i===0 ? { h:10 } : {});
    P.hsl = def; T.prepAll();
    const hp = box(SPOT.hair, 0)[0]; T.hslTakeRef(hp%W, Math.floor(hp/W)); const hairRef = P.hsl.sec[0].ref;
    const lipsQ = lips.map(qOf), lipsLch = [med(lipsQ.map(q => q[0])), med(lipsQ.map(q => q[1])), med(lipsQ.map(q => ((q[2]%360)+360)%360))];
    const redBox = box(SPOT.redPatch, 12), hairBox = box(SPOT.hair, 6);
    res.e = { lipsN:lips.length, lipsLch, skin:T.HS.skin, refRed:ref, refHair:hairRef,
      lipsSkinCore: lips.filter((i,k) => T.hsSkinW(...lipsQ[k]) >= 0.5).length/lips.length, rows:[] };
    for (const [name, hsl] of [['standard red', std], ['sample: chart red, reach 1', mk(i => i===0 ? { h:10, ref } : {})], ['sample: chart red, reach 0.5', mk(i => i===0 ? { h:10, ref, reach:0.5 } : {})],
                               ['sample: hair, reach 1', mk(i => i===0 ? { h:10, ref:hairRef } : {})], ['sample: hair, reach 0.5', mk(i => i===0 ? { h:10, ref:hairRef, reach:0.5 } : {})]])
      res.e.rows.push([name, share(hsl, lips, 0.1), share(hsl, lips, 0.5), share(hsl, redBox, 0.5), share(hsl, hairBox, 0.5)]);
    P.hsl = def; T.prepAll();
    return res;
  }, { SPOT, LIPS });
  for (const [name, nS, dS, nN, dN] of r.a) ok('(а) '+name+': skin core and neutral core unchanged', nS > 100 && nN > 100 && dS === 0 && dN === 0, 'skin core '+nS+' px changed '+dS+', neutral core '+nN+' px changed '+dN);
  ok('(б) sample on the chart red patch: unlike (weight 0) pixels bit-identical', r.b.zero > 1000 && r.b.zeroDiff === 0, 'weight 0: '+r.b.zero+' px, changed '+r.b.zeroDiff+'; sample L '+r.b.ref.L.toFixed(3)+' C '+r.b.ref.C.toFixed(3)+' h '+r.b.ref.h.toFixed(1));
  ok('(б) like the sample (weight ≥ 0.9) changes', r.b.strongN > 100 && r.b.strongMed > 2, r.b.strongN+' px, median ΔE00 '+r.b.strongMed.toFixed(2));
  ok('(б) red patch changes, green patch does not', r.b.redMed > 2 && r.b.greenMax === 0, 'red median ΔE00 '+r.b.redMed.toFixed(2)+', green max '+r.b.greenMax.toFixed(3));
  for (const [name, hf, cf, lf] of r.c) ok('(в) '+name+': no folds', hf === 0 && cf === 0 && lf === 0, 'hue '+hf+', chroma '+cf+', lightness '+lf);
  ok('(г) .cube with «Цвета» off: no # hsl line', !r.d.off.hasHsl && r.d.off.lines === 65*65*65);
  ok('(г) .cube with «Цвета» on: # hsl line', r.d.on.hasHsl && r.d.on.lines === 65*65*65);
  // strict ±1 everywhere does not hold even without «Цвета» (65-node trilinear vs exact maths at sharp edges, measured 2026-10-14):
  // pass = at most 0.05% of pixels off by more than 1 level; both numbers printed
  ok('(г) .cube applied to the frame = exact render ±1 level (≥ 99.95% of pixels)', r.d.on.over/r.d.on.n <= 0.0005, '«Цвета» on: max '+r.d.on.max+', pixels >1: '+r.d.on.over+' of '+r.d.on.n+' · off (reference): max '+r.d.off.max+', >1: '+r.d.off.over);
  console.log('(е) lips: '+r.e.lipsN+' px, median OkLCh L '+r.e.lipsLch[0].toFixed(3)+' C '+r.e.lipsLch[1].toFixed(3)+' h '+r.e.lipsLch[2].toFixed(1)
    +'; skin zone h '+r.e.skin.h.toFixed(1)+' ±'+r.e.skin.w.toFixed(1)+'; lips with skin weight ≥ 0.5: '+(r.e.lipsSkinCore*100).toFixed(1)+'%');
  console.log('    sample chart red: L '+r.e.refRed.L.toFixed(3)+' C '+r.e.refRed.C.toFixed(3)+' h '+r.e.refRed.h.toFixed(1)+' · sample hair: L '+r.e.refHair.L.toFixed(3)+' C '+r.e.refHair.C.toFixed(3)+' h '+r.e.refHair.h.toFixed(1));
  for (const [name, l1, l5, rp, hp] of r.e.rows) console.log('    '+name.padEnd(30)+' lips w>0.1 '+(l1*100).toFixed(1).padStart(5)+'%  w>0.5 '+(l5*100).toFixed(1).padStart(5)+'%  | chart red w>0.5 '+(rp*100).toFixed(0).padStart(3)+'%  hair w>0.5 '+(hp*100).toFixed(0).padStart(3)+'%');
  ok('(в–е) no page errors', !errs.length, errs.join('; '));
  await p.close(); fs.unlinkSync(tmp);

  // (д) the real page
  {
    const p = await b.newPage({ viewport:{ width:1440, height:900 } }); const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.addInitScript(mock); await p.goto('file://'+NEW); await p.waitForTimeout(2500);
    const hash = () => p.$eval('#img', c => { const d = c.getContext('2d').getImageData(0,0,c.width,c.height).data; let h = 0; for (let i=0;i<d.length;i+=7) h = (h*31+d[i])|0; return h; });
    const plates = await p.$$eval('.tools > .panel', a => a.map(e => [e.getAttribute('aria-label'), e.classList.contains('collapsed')]));
    const iC = plates.findIndex(x => x[0]==='Цвета'), iA = plates.findIndex(x => x[0]==='Аккорд');
    ok('(д) «Цвета» right after «Аккорд», open by default', iC === iA+1 && plates[iC][1] === false, plates.map(x => x[0]+(x[1]?'(св.)':'')).join(' · '));
    ok('(д) eight sectors in Alexey\'s order', (await p.$$eval('#hsSecs button', a => a.map(e => e.textContent).join(','))) === 'Красный,Оранжевый,Жёлтый,Зелёный,Аквамарин,Синий,Пурпурный,Маджента');
    await p.click('#hsSecs button[data-i="0"]'); await p.waitForTimeout(500);   // a settled re-render: marker dots scale with the fitted size
    const h0 = await hash();
    await p.click('#hsPick');
    const at = await p.$eval('#img', (c, f) => { const r = c.getBoundingClientRect(); return [r.left+f[0]*r.width, r.top+f[1]*r.height]; }, SPOT.redPatch);
    await p.mouse.click(at[0], at[1]); await p.waitForTimeout(400);
    const st = await p.$eval('#status', e => e.textContent), reach = await p.$eval('#hsReachRow', e => !e.hidden), mod = await p.$eval('#hsSecs button[data-i="0"]', e => e.classList.contains('mod'));
    const hp = await hash();
    ok('(д) sample by click on the photo', /Образец для «Красный»/.test(st) && reach && mod && hp === h0, st+' reach row '+reach+', sector marked '+mod+', photo unchanged '+(hp === h0));
    await p.$eval('#sHsH', e => { e.value = 20; e.dispatchEvent(new Event('input')); e.dispatchEvent(new Event('change')); });
    await p.$eval('#sHsS', e => { e.value = 60; e.dispatchEvent(new Event('input')); e.dispatchEvent(new Event('change')); }); await p.waitForTimeout(400);
    const h1 = await hash();
    ok('(д) sliders change the photo', h1 !== h0, 'output: '+(await p.$eval('#oHsH', e => e.textContent)));
    await p.click('#cHsMask'); await p.waitForTimeout(500); const hm = await hash();
    await p.click('#cHsMask'); await p.waitForTimeout(500);
    ok('(д) mask on and off', hm !== h1 && (await hash()) === h1);
    await p.click('#undo'); await p.waitForTimeout(300); await p.click('#undo'); await p.waitForTimeout(300); const hu = await hash();
    await p.click('#undo'); await p.waitForTimeout(300); const hu2 = await hash(), reach2 = await p.$eval('#hsReachRow', e => !e.hidden);
    await p.click('#redo'); await p.click('#redo'); await p.click('#redo'); await p.waitForTimeout(400);
    ok('(д) undo/redo walks sample and sliders', hu === h0 && hu2 === h0 && !reach2 && (await hash()) === h1);
    const cube = async () => { await p.$eval('#saveLut', e => e.click()); await p.waitForTimeout(600); const s = await p.evaluate(() => window.__saved.pop()); return Buffer.from(s[1]).toString('utf8'); };
    const c1 = await cube();
    await p.click('#resetAll'); await p.waitForTimeout(400);
    const c0 = await cube(), modAfter = await p.$$eval('#hsSecs button.mod', a => a.length);
    ok('(д) LUT carries # hsl line; «Сбросить всё» clears «Цвета»', /# hsl \(requested>applied\): red\(h=20>/.test(c1) && !c0.includes('# hsl') && modAfter === 0, (c1.match(/# hsl.*/) || [''])[0].slice(0, 120));
    ok('(д) no page errors', !errs.length, errs.join('; '));
    await p.close();
  }
  await b.close();
  console.log(fails ? fails+' FAILED' : 'ALL PASS'); process.exit(fails ? 1 : 0);
})();
