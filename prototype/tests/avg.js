// «Усреднение тонов» checks. Run from prototype/build:  node ../tests/avg.js
// (а) «Сближение» 0, or nothing kept: output bit-identical to the tool's default (every pixel, LUT 33, .cube text)
// (б) skin core and neutral core do not change (0 pixels) at «Сближение» 100 with several kept sets
// (в) a kept sector does not move: pixels within ±9.9° of a kept hue (at the stage's input) are bit-identical
// (г) hue spread (circular SD, chroma-weighted, without skin and neutrals) after < before — demo portrait, several kept sets printed
// (д) the exported .cube (sRGB 65), applied to the frame, against the exact per-pixel render: share of pixels off by more than 1 level
// (е) the plate in the real page: place, order, toggles, slider, readout, undo/redo, reset all, «# avg» line in the LUT
// BREAK=1 makes the stage ignore skin, neutrals and kept zones: (б) and (в) must turn red.
const { chromium } = require('playwright');
const fs = require('fs');
const NEW = process.cwd()+'/complement_built.html', TEST = process.cwd()+'/test_built.html';
const launch = () => chromium.launch({ ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
let fails = 0; const ok = (name, cond, info) => { console.log((cond ? 'PASS ' : 'FAIL ')+name+(info ? '  '+info : '')); if (!cond) fails++; };
const mock = () => { window.__saved = []; window.claude = { use: async () => ({ save: async ({ filename, data }) => {
  const b = new Uint8Array(await data.arrayBuffer()); window.__saved.push([filename, Array.from(b)]); } }) }; };

(async () => {
  const b = await launch();
  let html = fs.readFileSync(TEST, 'utf8');
  if (process.env.BREAK){
    const g = "  const wn = wnAt(C); if (!wn) return [L,C,h];\n  const D = avD(h); if (!D) return [L,C,h];\n  return [L, C, h + AV.s*D*(1-hsSkinW(L,C,h))*wn];\n";
    if (!html.includes(g)) { console.log('BREAK: stage string not found'); process.exit(2); }
    html = html.replace(g, "  return [L, C, h + AV.s*(avD(h)+3)];\n"); console.log('BREAK: stage ignores skin, neutrals and kept zones');
  }
  const tmp = process.cwd()+'/avg_test_tmp.html'; fs.writeFileSync(tmp, html);
  const p = await b.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://'+tmp); await p.waitForTimeout(2500);
  const r = await p.evaluate(() => {
    const T = window.__t, P = T.P, res = {};
    const d = T.srcData.data, n = d.length/4, all = Array.from({ length:n }, (_,i) => i), every = all.filter(i => i%3 === 0);
    const keepOf = a => Object.freeze([0,1,2,3,4,5,6,7].map(i => a.includes(i)));
    const set = (keep, amt) => { P.avgKeep = keepOf(keep); P.avgAmt = amt; T.prepAll(); };
    const rgb = i => [d[i*4]/255, d[i*4+1]/255, d[i*4+2]/255];
    const outAll = (idx = all) => { const o = new Float64Array(n*3); for (const i of idx){ const v = T.xf(...rgb(i), 'srgb'); o[i*3]=v[0]; o[i*3+1]=v[1]; o[i*3+2]=v[2]; } return o; };
    const eqArr = (a, b) => { if (a.length !== b.length) return false; for (let i=0;i<a.length;i++) if (a[i] !== b[i]) return false; return true; };
    const diffPx = (a, b, idx) => idx.filter(i => a[i*3]!==b[i*3] || a[i*3+1]!==b[i*3+1] || a[i*3+2]!==b[i*3+2]).length;
    // stage input (after «Цвета»), the same for every averaging setting
    set([], 0);
    const qIn = all.map(i => T.xfPre(...rgb(i), 'srgb'));   // «Цвета» off in this test: xfPre = stage input
    const base = outAll(), baseLut = T.buildLUT(33, 'srgb'), baseCube = T.cubeText(33, 'srgb');

    // (а)
    res.a = [];
    for (const [name, keep, amt] of [['«Сближение» 0, orange and blue kept', [1,5], 0], ['nothing kept, «Сближение» 100', [], 100]]){
      set(keep, amt); const o = outAll();
      res.a.push([name, eqArr(o, base), eqArr(T.buildLUT(33, 'srgb'), baseLut), T.cubeText(33, 'srgb') === baseCube, T.AV.on]);
    }

    // (б), (в) — skin core as in hsl.js: pixels of the skin marker cloud whose skin weight is 1; neutrals: chroma at or below the grey
    // threshold (wnAt = 0); every 3rd pixel for the rest
    const skinCore = Array.from(T.cloudOf('skin')).filter(i => qIn[i][1] > 1e-5 && T.hsSkinW(...qIn[i]) >= 1-1e-12);
    const neutral = every.filter(i => T.wnAt(qIn[i][1]) === 0);
    const check = Array.from(new Set(skinCore.concat(every)));
    res.b = []; res.c = [];
    for (const [name, keep] of [['orange', [1]], ['blue (skin border)', [5]], ['orange + blue', [1,5]], ['red, green, blue', [0,3,5]], ['all eight', [0,1,2,3,4,5,6,7]]]){
      set(keep, 100); const o = outAll(check);
      res.b.push([name, skinCore.length, diffPx(o, base, skinCore), neutral.length, diffPx(o, base, neutral), Math.round(T.AV.s*100)]);
      const hk = T.AV.keep.map(k => k.h);
      const inZone = every.filter(k => qIn[k][1] > 1e-5 && hk.some(h => Math.abs(((qIn[k][2]-h+540)%360)-180) <= 9.9));
      // and the averaging moves something at all
      let moved = 0; for (const i of every) if (o[i*3]!==base[i*3] || o[i*3+1]!==base[i*3+1] || o[i*3+2]!==base[i*3+2]) moved++;
      res.c.push([name, inZone.length, diffPx(o, base, inZone), moved]);
    }
    // a «Цвета» sample sets the kept hue; «Цвета» turning a sector moves the kept hue with it
    const Z = { h:0, s:0, l:0, ref:null, reach:1 };
    const ref = Object.freeze({ L:0.62, C:0.12, h:70 });
    P.hsl = Object.freeze({ sec:Object.freeze(Array.from({length:8}, (_,i) => Object.freeze(i===1 ? { ...Z, ref } : i===5 ? { ...Z, h:20 } : Z))) });
    set([1,5], 100);
    res.cRef = [T.AV.keep.map(k => [k.i, +k.h.toFixed(2), k.ref]), T.HS_C[5] + T.HS.h[5], T.HS.any];
    P.hsl = T.defaultHsl(); T.prepAll();

    // (г) spread, every pixel
    res.g = [];
    for (const [name, keep, amt] of [['orange 100%', [1], 100], ['orange 50%', [1], 50], ['orange + blue 100%', [1,5], 100], ['blue 100%', [5], 100], ['red, green, blue 100%', [0,3,5], 100]]){
      set(keep, amt); const sp = T.avSpread(all.map(i => i*4));
      res.g.push([name, sp.before, sp.after, sp.nearBefore, sp.nearAfter, Math.round(T.AV.s*100)]);
    }

    // (д) .cube 65 applied (trilinear) vs the exact render, in 8-bit levels
    const cubeVsRender = () => {
      const txt = T.cubeText(65, 'srgb'), lines = txt.split('\n').filter(l => /^[0-9.\-]+ [0-9.\-]+ [0-9.\-]+$/.test(l));
      const N = 65, lut = new Float32Array(N*N*N*3); lines.forEach((l,k) => { const v = l.split(' ').map(Number); lut[k*3]=v[0]; lut[k*3+1]=v[1]; lut[k*3+2]=v[2]; });
      const dst = new Uint8ClampedArray(d.length); T.applyLUT(d, dst, lut, N);
      let mx = 0, over = 0;
      for (let i=0;i<n;i++){ const o = T.xf(...rgb(i), 'srgb'); let m = 0; for (let c=0;c<3;c++) m = Math.max(m, Math.abs(dst[i*4+c] - Math.round(o[c]*255))); mx = Math.max(mx, m); if (m > 1) over++; }
      return { lines:lines.length, avgLine:(txt.match(/# avg.*/) || [''])[0], max:mx, over, n };
    };
    set([], 0); res.d = { off:cubeVsRender() };
    set([1], 100); res.d.on = cubeVsRender();
    set([1,5], 100); res.d.on2 = cubeVsRender();
    set([], 0);
    return res;
  });
  for (const [name, px, lut, cube, on] of r.a) ok('(а) '+name+': bit-identical', px && lut && cube && !on, 'pixels '+px+', LUT 33 '+lut+', .cube text '+cube+', stage on '+on);
  for (const [name, nS, dS, nN, dN, s] of r.b) ok('(б) kept '+name+' 100%: skin core and neutrals unchanged', nS > 100 && nN > 100 && dS === 0 && dN === 0, 'skin core '+nS+' px changed '+dS+', neutrals '+nN+' px changed '+dN+' (applied '+s+'%)');
  for (const [name, nZ, dZ, moved] of r.c) ok('(в) kept '+name+' 100%: pixels at a kept hue (±9.9°) unchanged, others move', nZ > 100 && dZ === 0 && moved > 1000, 'at kept hue '+nZ+' px changed '+dZ+'; changed in the frame '+moved+' px');
  ok('(в) kept hue from a «Цвета» sample and from a turned sector', r.cRef[0][0][1] === 70 && r.cRef[0][0][2] && Math.abs(r.cRef[0][1][1] - ((r.cRef[1]%360)+360)%360) < 0.006 && r.cRef[2],
     'kept '+JSON.stringify(r.cRef[0])+'; blue centre + applied turn '+r.cRef[1].toFixed(2));
  for (const [name, b0, a0, n0, n1, s] of r.g) console.log('    spread '+name.padEnd(24)+' '+b0.toFixed(1)+'° → '+a0.toFixed(1)+'°   to nearest kept '+n0.toFixed(1)+'° → '+n1.toFixed(1)+'°   (applied '+s+'%)');
  ok('(г) hue spread after < before (orange kept, 100%)', r.g[0][2] < r.g[0][1], r.g[0][1].toFixed(1)+'° → '+r.g[0][2].toFixed(1)+'°');
  ok('(г) mean distance to the nearest kept hue falls for every kept set', r.g.every(x => x[4] < x[3]));
  const pc = x => (x.over/x.n*100).toFixed(3)+'% ('+x.over+' of '+x.n+'), max '+x.max;
  ok('(д) .cube with the tool off: no # avg line', r.d.off.lines === 65**3 && !r.d.off.avgLine);
  ok('(д) .cube with the tool on: # avg line', r.d.on.lines === 65**3 && /# avg \(requested>applied, %\): keep=orange@53\.0 .*amt=100>/.test(r.d.on.avgLine), r.d.on.avgLine);
  // measurement, no pass/fail: strict ±1 everywhere does not hold even without the tool (65-node trilinear vs exact maths at sharp edges);
  // hsl.js holds «Цвета» to ≤ 0.05%, the averaging stretches hues up to 2.4× near a watershed and does not meet that bar (2026-10-15)
  console.log('    .cube 65 applied vs exact render, pixels off by more than 1 level — tool off: '+pc(r.d.off)+' · orange 100%: '+pc(r.d.on)+' · orange+blue 100%: '+pc(r.d.on2));
  ok('(а–д) no page errors', !errs.length, errs.join('; '));
  await p.close(); fs.unlinkSync(tmp);

  // (е) the real page
  {
    const p = await b.newPage({ viewport:{ width:1440, height:900 } }); const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.addInitScript(mock); await p.goto('file://'+NEW); await p.waitForTimeout(2500);
    const hash = () => p.$eval('#img', c => { const d = c.getContext('2d').getImageData(0,0,c.width,c.height).data; let h = 0; for (let i=0;i<d.length;i+=7) h = (h*31+d[i])|0; return h; });
    const plates = await p.$$eval('.tools > .panel', a => a.map(e => [e.getAttribute('aria-label'), e.classList.contains('collapsed')]));
    const iA = plates.findIndex(x => x[0]==='Усреднение тонов'), iC = plates.findIndex(x => x[0]==='Цвета');
    ok('(е) «Усреднение тонов» right after «Цвета», open by default', iA === iC+1 && plates[iA][1] === false, plates.map(x => x[0]+(x[1]?'(св.)':'')).join(' · '));
    const names = await p.$$eval('#avSecs button', a => a.map(e => e.textContent).join(','));
    ok('(е) eight sectors in the same order as «Цвета»', names === await p.$$eval('#hsSecs button', a => a.map(e => e.textContent).join(',')), names);
    await p.$eval('#avgPanel', e => e.scrollIntoView());
    await p.click('#hsSecs button[data-i="0"]'); await p.waitForTimeout(500);   // a settled re-render: marker dots scale with the fitted size
    const h0 = await hash(), info0 = await p.$eval('#avInfo', e => e.textContent);
    await p.click('#avSecs button[data-i="1"]'); await p.waitForTimeout(400);
    const h1 = await hash(), pressed = await p.$eval('#avSecs button[data-i="1"]', e => e.getAttribute('aria-pressed'));
    ok('(е) toggle «Оставить» alone (Сближение 0) does not change the photo', pressed === 'true' && h1 === h0, 'pressed '+pressed);
    await p.$eval('#sAvg', e => { e.value = 80; e.dispatchEvent(new Event('input')); e.dispatchEvent(new Event('change')); }); await p.waitForTimeout(600);
    const h2 = await hash(), info = await p.$eval('#avInfo', e => e.innerText), out = await p.$eval('#oAvg', e => e.textContent);
    ok('(е) «Сближение» changes the photo; readout shows spread before → after', h2 !== h0 && /Разброс оттенков: [\d.]+° → [\d.]+°/.test(info) && /^80%/.test(out), out+' | '+info.replace(/\n/g, ' | '));
    await p.click('#undo'); await p.waitForTimeout(400); const hu = await hash();
    await p.click('#undo'); await p.waitForTimeout(400); const hu2 = await hash(), pr2 = await p.$eval('#avSecs button[data-i="1"]', e => e.getAttribute('aria-pressed'));
    await p.click('#redo'); await p.click('#redo'); await p.waitForTimeout(500);
    ok('(е) undo/redo walks slider and toggle', hu === h0 && hu2 === h0 && pr2 === 'false' && (await hash()) === h2);
    const cube = async () => { await p.$eval('#saveLut', e => e.click()); await p.waitForFunction(() => window.__saved.length > 0, null, { timeout:20000 }); const s = await p.evaluate(() => window.__saved.pop()); return Buffer.from(s[1]).toString('utf8'); };
    const c1 = await cube();
    await p.click('#resetAll'); await p.waitForTimeout(500);
    const c0 = await cube(), pressedAfter = await p.$$eval('#avSecs button[aria-pressed="true"]', a => a.length), amtAfter = await p.$eval('#sAvg', e => e.value);
    ok('(е) LUT carries # avg line; «Сбросить всё» clears the tool', /# avg \(requested>applied, %\): keep=orange@/.test(c1) && !c0.includes('# avg') && pressedAfter === 0 && amtAfter === '0', (c1.match(/# avg.*/) || [''])[0]);
    ok('(е) readout without kept sectors', /Ничего не оставлено/.test(info0), info0.slice(0, 80));
    ok('(е) no page errors', !errs.length, errs.join('; '));
    await p.close();
  }
  await b.close();
  console.log(fails ? fails+' FAILED' : 'ALL PASS'); process.exit(fails ? 1 : 0);
})();
