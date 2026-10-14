// Curve tool checks. Run from prototype/build:  OLD=<old complement_built.html> node ../tests/curves.js
// (а) identity curves: preview, LUT sRGB/P3 × 33/65, PNG, JPG (7 outputs) byte-identical to OLD (demo state and an edited state)
// (б) 200 random gesture sequences per channel through the fold guard: no channel result ever falls
// (в) LRGB L and Soft keep OkLab hue within 0.5° on a colour grid
// (г) Soft Light equals the Photoshop formula at 5 points (numbers written out below)
// (the curve graph sits in the scrolling tool column of the desktop shell: scrollIntoView before taking its rect)
// BREAK=1 removes the fold guard from the page: (б) must turn red.
const { chromium } = require('playwright');
const crypto = require('crypto'), fs = require('fs');
const NEW = process.cwd()+'/complement_built.html', TEST = process.cwd()+'/test_built.html', OLD = process.env.OLD;
const launch = () => chromium.launch({ ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
let fails = 0; const ok = (name, cond, info) => { console.log((cond ? 'PASS ' : 'FAIL ')+name+(info ? '  '+info : '')); if (!cond) fails++; };
const mock = () => { window.__saved = []; window.claude = { use: async () => ({ save: async ({ filename, data }) => {
  const b = new Uint8Array(await data.arrayBuffer()); window.__saved.push([filename, Array.from(b)]); } }) }; };
async function outputs(b, file, edit){
  const p = await b.newPage({ viewport:{ width:1440, height:1200 } }); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.addInitScript(mock); await p.goto('file://'+file); await p.waitForTimeout(2500);
  await p.click('#unfoldAll'); await p.waitForTimeout(300);
  if (edit){
    await p.$eval('#sRotAll', e => { e.value=25; e.dispatchEvent(new Event('input')); e.dispatchEvent(new Event('change')); });
    await p.click('#skinToTarget'); await p.waitForTimeout(400);
    if (edit === 'curveThenReset'){ // bend a curve in every tab, then reset each tab: must be identity again
      for (const tab of ['lrgb','lab','soft']){ await p.click(`#cvTabs button[data-tab=${tab}]`);
        const r = await p.$eval('#cvCv', e => { e.scrollIntoView({ block:'center' }); const r = e.getBoundingClientRect(); return [r.left, r.top, r.width]; });
        await p.mouse.move(r[0]+r[2]*0.4, r[1]+r[2]*0.5); await p.mouse.down(); await p.mouse.move(r[0]+r[2]*0.4, r[1]+r[2]*0.3, { steps:4 }); await p.mouse.up();
        await p.click('#cvReset'); }
      await p.waitForTimeout(400);
    }
  }
  const h = {};
  h.preview = crypto.createHash('sha256').update(Buffer.from(await p.$eval('#img', c => Array.from(c.getContext('2d').getImageData(0,0,c.width,c.height).data)))).digest('hex');
  for (const [sp, n] of [['spS','n33'],['spS','n65'],['spP','n33'],['spP','n65']]){ await p.click('#'+sp); await p.click('#'+n); await p.click('#saveLut'); await p.waitForTimeout(300); }
  await p.click('#savePng'); await p.waitForTimeout(2500); await p.click('#saveJpg'); await p.waitForTimeout(2500);
  for (const [name, bytes] of await p.evaluate(() => window.__saved)) h[name+'#'+Object.keys(h).filter(k=>k.startsWith(name)).length] = crypto.createHash('sha256').update(Buffer.from(bytes)).digest('hex');
  await p.close(); return { h, errs };
}
(async () => {
  const b = await launch();
  // (а)
  if (!OLD) console.log('SKIP (а): set OLD=<complement_built.html of the code before curves>');
  else for (const [label, edit, ref] of [['demo', null, null], ['edited', 'plain', 'plain'], ['edited, curves bent then reset', 'curveThenReset', 'plain']]){
    const o = await outputs(b, OLD, ref), n = await outputs(b, NEW, edit);
    const keys = Object.keys(o.h), diff = keys.filter(k => o.h[k] !== n.h[k]);
    ok('(а) byte-identical '+label+': '+keys.length+' outputs', keys.length === 7 && diff.length === 0 && Object.keys(n.h).length === 7, diff.length ? 'differ: '+diff.join(',') : '');
    ok('(а) no page errors '+label, !o.errs.length && !n.errs.length, n.errs.join('; '));
  }
  // (д) gestures in the real page: graph drag, on-image drag, undo/redo, reset all, before/after, LUT comment line
  {
    const p = await b.newPage({ viewport:{ width:1440, height:1100 } }); const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.addInitScript(mock); await p.goto('file://'+NEW); await p.waitForTimeout(2500);
    await p.click('#foldAll'); await p.click('h2:has-text("Кривая")'); await p.waitForTimeout(300);
    const hash = () => p.$eval('#img', c => { const d = c.getContext('2d').getImageData(0,0,c.width,c.height).data; let h = 0; for (let i=0;i<d.length;i+=7) h = (h*31+d[i])|0; return h; });
    const h0 = await hash();
    const g = await p.$eval('#cvCv', e => { e.scrollIntoView({ block:'center' }); const r = e.getBoundingClientRect(); return { x:r.left, y:r.top, k:r.width/276 }; });
    const at = (x,y) => [g.x+(16+x*256)*g.k, g.y+(4+(1-y)*256)*g.k];
    await p.mouse.move(...at(0.5,0.5)); await p.mouse.down(); await p.mouse.move(...at(0.5,0.62), { steps:5 }); await p.mouse.up(); await p.waitForTimeout(400);
    const h1 = await hash(), mod = await p.$eval('#cvChans button[data-ch=L]', e => e.classList.contains('mod'));
    ok('(д) graph drag changes the photo and marks channel L', h1 !== h0 && mod);
    // a point dragged past its neighbour stops at it (no fold): drag the new point far down-right
    await p.mouse.move(...at(0.5,0.62)); await p.mouse.down(); await p.mouse.move(...at(0.98,0.02), { steps:5 }); await p.mouse.up();
    const pin = await p.$eval('#cvIn', e => e.value), pout = await p.$eval('#cvOut', e => e.value);
    ok('(д) point stopped at its neighbours, not past them', Number(pin) < 255 && Number(pout) >= 0, 'in '+pin+' out '+pout);
    await p.click('#undo'); await p.waitForTimeout(300); ok('(д) undo returns the first bend', await hash() === h1);
    await p.click('#undo'); await p.waitForTimeout(300); ok('(д) undo returns the photo', await hash() === h0);
    await p.click('#redo'); await p.waitForTimeout(300); ok('(д) redo bends again', await hash() === h1);
    await p.click('#vBefore'); await p.waitForTimeout(300); const hb = await hash();
    await p.click('#vAfter'); await p.waitForTimeout(300); ok('(д) До/После toggles the bent photo', hb !== h1 && await hash() === h1);
    await p.click('#unfoldAll'); await p.click('#saveLut'); await p.waitForTimeout(500);
    const lut = await p.evaluate(() => { const b = window.__saved[window.__saved.length-1][1]; return new TextDecoder().decode(new Uint8Array(b.slice(0, 2000))); });
    ok('(д) LUT carries a "# curves:" comment line', /# curves: lrgb\.L=/.test(lut));
    await p.click('#foldAll'); await p.click('h2:has-text("Кривая")');
    // on-image: Soft tab, picker mode, drag up on the cheek
    const chips0 = await p.$eval('#chips', e => e.children.length);
    await p.click('#cvTabs button[data-tab=soft]'); await p.click('#cvModeFrame');
    const im = await p.$eval('#img', e => { const r = e.getBoundingClientRect(); return { x:r.left, y:r.top, w:r.width, h:r.height }; });
    const cx = im.x+im.w*(840/1717), cy = im.y+im.h*(820/2576);
    await p.mouse.move(cx, cy); await p.waitForTimeout(200);
    const hov = await p.$eval('#cvHover', e => e.textContent);
    await p.mouse.down(); await p.mouse.move(cx, cy-40, { steps:5 }); await p.mouse.up(); await p.waitForTimeout(400);
    const h2 = await hash(), chips1 = await p.$eval('#chips', e => e.children.length), cur = await p.$eval('#img', e => e.classList.contains('curvepick'));
    ok('(д) on-image drag bends Soft, no marker added, cursor ns-resize', h2 !== h1 && chips1 === chips0 && cur, 'hover "'+hov.trim()+'"');
    const sp = await p.$eval('#cvOut', e => Number(e.value)); ok('(д) drag up raised the layer above 128', sp > 128, 'layer '+sp);
    await p.click('#resetAll'); await p.waitForTimeout(400);
    const allId = await p.$$eval('#cvTabs button', bs => bs.every(b => !b.classList.contains('mod')));
    ok('(д) «Сбросить всё» clears every curve', allId);
    ok('(д) no page errors', !errs.length, errs.join('; '));
    await p.close();
  }
  // (б)–(г) on the test build with hooks
  let html = fs.readFileSync(TEST, 'utf8');
  if (process.env.BREAK){
    const g1 = "    y = Math.max(i>0 ? pts[i-1][1] : 0, Math.min(i<n-1 ? pts[i+1][1] : 1, y));\n", g2 = "const q = setAt(pts, i, x, y); if (chanOk(q, true)) return q;";
    if (!html.includes(g1) || !html.includes(g2)) { console.log('BREAK: guard strings not found'); process.exit(2); }
    html = html.replace(g1, '').replace(g2, 'const q = setAt(pts, i, x, y); return q;'); console.log('BREAK: fold guard removed');
  }
  const tmp = process.cwd()+'/curves_test_tmp.html'; fs.writeFileSync(tmp, html);
  const p = await b.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://'+tmp); await p.waitForTimeout(2500);
  const r = await p.evaluate(() => {
    const T = window.__t; let seed = 42; const rnd = () => (seed = (seed*1103515245+12345) & 0x7fffffff) / 0x7fffffff;
    const chans = [['lrgb','L'],['lrgb','R'],['lrgb','G'],['lrgb','B'],['lab','L'],['lab','a'],['lab','b'],['soft','L']], res = {};
    const randomCurve = soft => {
      let pts = soft ? [[0,0.5],[1,0.5]] : [[0,0],[1,1]];
      for (let s=0; s<8; s++){
        if (rnd() < 0.5){ const a = T.curveAdd(pts, rnd(), soft); if (a){ pts = a.pts; pts = T.curveMove(pts, a.i, a.pts[a.i][0]+(rnd()-0.5)*0.2, rnd(), soft); } }
        else { const i = Math.floor(rnd()*pts.length); pts = T.curveMove(pts, i, rnd(), rnd(), soft); }
      }
      return pts;
    };
    for (const [tab, ch] of chans){
      const soft = tab === 'soft'; let bad = 0, maxDrop = 0, bent = 0, pipeDrop = 0;
      for (let k=0; k<200; k++){
        const pts = randomCurve(soft), T2 = T.chanTable(pts, soft);
        if (pts.length > 2 || pts.some(q => soft ? q[1] !== 0.5 : q[0] !== q[1])) bent++;
        let f = false; for (let j=1;j<T2.length;j++){ const d = T2[j-1]-T2[j]; if (d > 1e-9){ f = true; maxDrop = Math.max(maxDrop, d); } }
        // the same curve through the real pipeline: a grey ramp (L, Soft, Lab L) or a single-channel ramp (R, G, B) must not fall
        const c = T.defaultCurves(); T.P.curves = Object.freeze({ ...c, [tab]: Object.freeze({ ...c[tab], [ch]: pts }) }); T.prepAll();
        let prev = -1, pd = 0;
        for (let v=0; v<=1.0001; v+=1/255){
          // R, G, B: that channel's output; Lab L: luminance Y (L* is monotone in Y); LRGB L and Soft: output OkLab L, which is what they set
          const okL = o3 => { const li = o3.map(c => c <= 0.04045 ? c/12.92 : Math.pow((c+0.055)/1.055, 2.4)); return 0.2104542553*Math.cbrt(0.4122214708*li[0]+0.5363325363*li[1]+0.0514459929*li[2])+0.7936177850*Math.cbrt(0.2119034982*li[0]+0.6806995451*li[1]+0.1073969566*li[2])-0.0040720468*Math.cbrt(0.0883024619*li[0]+0.2817188376*li[1]+0.6299787005*li[2]); };
          const o = ch==='R' ? T.xf(v,0.5,0.5,'srgb')[0] : ch==='G' ? T.xf(0.5,v,0.5,'srgb')[1] : ch==='B' ? T.xf(0.5,0.5,v,'srgb')[2]
            : tab==='lab' ? (o3 => { const li = o3.map(c => c <= 0.04045 ? c/12.92 : Math.pow((c+0.055)/1.055, 2.4)); return 0.2126*li[0]+0.7152*li[1]+0.0722*li[2]; })(T.xf(v,v,v,'srgb'))
            : okL(T.xf(v,v,v,'srgb'));
          if (ch!=='a' && ch!=='b'){ pd = Math.max(pd, prev-o); if (o < prev-1e-4) f = true; } prev = o;   // 1e-4: the gamut mapper's own jitter is ~1e-5 even with no curve
        }
        if (f){ bad++; } pipeDrop = Math.max(pipeDrop, pd);
      }
      res[tab+'.'+ch] = { bad, bent, maxDrop, pipeDrop };
    }
    T.P.curves = T.defaultCurves(); T.prepAll();
    // (в) hue kept by LRGB L and Soft
    const lch = o => { const lin = o.map(c => c <= 0.04045 ? c/12.92 : Math.pow((c+0.055)/1.055, 2.4));
      const l = Math.cbrt(0.4122214708*lin[0]+0.5363325363*lin[1]+0.0514459929*lin[2]), m = Math.cbrt(0.2119034982*lin[0]+0.6806995451*lin[1]+0.1073969566*lin[2]), s = Math.cbrt(0.0883024619*lin[0]+0.2817188376*lin[1]+0.6299787005*lin[2]);
      const a = 1.9779984951*l-2.4285922050*m+0.4505937099*s, bb = 0.0259040371*l+0.7827717662*m-0.8086757660*s; return [Math.hypot(a,bb), Math.atan2(bb,a)*180/Math.PI]; };
    const hueTest = (tab, pts) => {
      const c = T.defaultCurves(); T.P.curves = T.defaultCurves(); T.prepAll();
      const grid = []; for (let r=0;r<=1.0001;r+=1/8) for (let g=0;g<=1.0001;g+=1/8) for (let bl=0;bl<=1.0001;bl+=1/8) grid.push([r,g,bl, lch(T.xf(r,g,bl,'srgb'))]);
      T.P.curves = Object.freeze({ ...c, [tab]: Object.freeze({ ...c[tab], L: pts }) }); T.prepAll();
      let worst = 0, n = 0;
      for (const [r,g,bl,base] of grid){ const now = lch(T.xf(r,g,bl,'srgb')); if (base[0] < 0.02 || now[0] < 0.02) continue; n++;
        worst = Math.max(worst, Math.abs(((now[1]-base[1]+540)%360)-180)); }
      return { worst, n };
    };
    const hueL = hueTest('lrgb', [[0,0],[0.25,0.15],[0.6,0.75],[1,1]]), hueS = hueTest('soft', [[0,0.5],[0.2,0.3],[0.5,0.7],[0.85,0.4],[1,0.5]]);
    T.P.curves = T.defaultCurves(); T.prepAll();
    // (г) Soft Light at 5 points: [base a, blend b, expected by the Photoshop formula]
    const pts5 = [[0.25,0.25,0.15625],[0.5,0.75,0.603553390593],[0.8,0.3,0.736],[0.1,0.9,0.272982212813],[0.6,0.5,0.6]];
    const sl = pts5.map(([a,b,e]) => [a,b,e,T.softLight(a,b)]);
    return { res, hueL, hueS, sl };
  });
  for (const k in r.res) ok('(б) no folds '+k+' ('+r.res[k].bent+'/200 bent)', r.res[k].bad === 0 && r.res[k].bent >= 150, 'folded '+r.res[k].bad+', curve drop '+r.res[k].maxDrop.toExponential(2)+', pipeline drop '+r.res[k].pipeDrop.toExponential(2));
  ok('(в) LRGB L keeps hue', r.hueL.worst <= 0.5, 'max '+r.hueL.worst.toFixed(3)+'° over '+r.hueL.n+' colours');
  ok('(в) Soft keeps hue', r.hueS.worst <= 0.5, 'max '+r.hueS.worst.toFixed(3)+'° over '+r.hueS.n+' colours');
  for (const [a,bb,e,g] of r.sl) ok('(г) softLight('+a+', '+bb+') = '+e, Math.abs(g-e) < 1e-9, 'got '+g.toFixed(12));
  ok('(г) differs from W3C at (0.1, 0.9): W3C 0.2568', Math.abs(r.sl[3][3]-0.2568) > 0.01);
  ok('no page errors (hooks)', !errs.length, errs.join('; '));
  fs.unlinkSync(tmp); await b.close();
  console.log(fails ? 'FAILED '+fails : 'ALL PASS'); process.exit(fails ? 1 : 0);
})();
