const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
  const p = await b.newPage();
  await p.goto('file://'+process.cwd()+'/test_built.html'); await p.waitForTimeout(2500);
  const r = await p.evaluate(() => {
    const T = window.__t, out = [];
    const cfgs = [
      {rotAll:30},{rotAll:-45},{rotOpp:60,spread:30,mode:'split'},{rotAll:60,rotOpp:-60},
      {rotAll:-60,skinCf:1.5,skinDh:15},{rotAll:45,skinCf:0.5,skinDh:-15},{mode:'triad',rotAll:20,spread:-30}];
    for (const c of cfgs){
      Object.assign(T.P, {mode:'pair',rotAll:0,rotOpp:0,spread:0,skinCf:1,skinDh:0}, c); T.prepAll();
      let folds = 0, cfold = 0;
      for (let L=0.2; L<=0.98; L+=0.04) for (let C=0.01; C<=0.3; C+=0.01){
        let prev = null, acc = 0, first = null;
        for (let h=0; h<=360; h+=0.5){
          const n = T.normLch(L,C,h); const nh = T.transformHue(L,C,n[1]);
          if (prev!==null){ let d = ((nh-prev+540)%360)-180; if (d < -1e-6) folds++; acc += d; }
          prev = nh;
        }
        if (Math.abs(acc-360) > 1) folds++;
      }
      // chroma monotonic in C for skin adjust
      for (let L=0.3; L<=0.95; L+=0.05) for (let h=0; h<360; h+=3){ let pc=-1; for (let C=0.002; C<=0.3; C+=0.002){ const n=T.normLch(L,C,h); if (n[0] < pc-1e-9) cfold++; pc=n[0]; } }
      out.push(JSON.stringify(c)+' hueFolds='+folds+' chromaFolds='+cfold);
    }
    // «Цвета» (HSL by sectors): extreme sliders, with and without samples. Grids are off the guard's own grid on purpose.
    // hue/chroma/lightFolds — the stage alone; chain* — skin correction + chord + stage, i.e. what a pixel goes through.
    // Known (2026-10-14): chainChromaFolds is not 0 with skin correction AND a turned chord AND sector chroma boost — drops ≤ 1.2e-4
    // OkLab C on the skin correction's sharp edge, between the guard's grid lines; a denser guard grid costs ~220 ms a frame.
    const Z = { h:0, s:0, l:0, ref:null, reach:1 };
    const sec = f => Object.freeze({ sec:Object.freeze(Array.from({length:8}, (_,i) => Object.freeze({ ...Z, ...f(i) }))) });
    const lipsRef = Object.freeze({ L:0.60, C:0.10, h:20 }), redRef = Object.freeze({ L:0.55, C:0.17, h:28 }), oraRef = Object.freeze({ L:0.70, C:0.15, h:52 });
    const hcfgs = [
      ['all +', {}, sec(() => ({ h:30, s:100, l:100 }))],
      ['all -', {}, sec(() => ({ h:-30, s:-100, l:-100 }))],
      ['alternating', {}, sec(i => i%2 ? { h:30, s:100, l:-100 } : { h:-30, s:-100, l:100 })],
      ['red+30 orange-30', {}, sec(i => i===0 ? { h:30 } : i===1 ? { h:-30 } : {})],
      ['red sample reach0.5', {}, sec(i => i===0 ? { h:30, s:-100, l:100, ref:lipsRef, reach:0.5 } : {})],
      ['red+orange samples', {}, sec(i => i===0 ? { h:-30, s:100, l:-100, ref:redRef, reach:2 } : i===1 ? { h:30, s:-100, l:100, ref:oraRef, reach:0.5 } : { h:i%2?30:-30 })],
      ['all + with chord', { rotAll:45, skinCf:1.5, skinDh:15 }, sec(() => ({ h:30, s:100, l:100 }))],
      ['samples with chord', { mode:'split', rotOpp:60, spread:30 }, sec(i => i===0 ? { h:30, s:-100, l:-100, ref:lipsRef, reach:0.5 } : i===5 ? { h:-30, s:100, l:100 } : {})]];
    for (const [name, c, hsl] of hcfgs){
      Object.assign(T.P, {mode:'pair',rotAll:0,rotOpp:0,spread:0,skinCf:1,skinDh:0}, c); T.P.hsl = hsl; T.prepAll();
      let hf = 0, chf = 0, cf = 0, ccf = 0, ccd = 0, lf = 0, clf = 0;
      for (let L=0.14; L<=0.98; L+=0.03) for (let C=0.011; C<=0.3; C+=0.007){
        let prev = null, acc = 0, prev2 = null, acc2 = 0;
        for (let h=0; h<=360; h+=0.5){
          const nh = T.hslStage(L,C,h)[2];
          if (prev!==null){ const d = ((nh-prev+540)%360)-180; if (d < -1e-6) hf++; acc += d; }
          prev = nh;
          const n = T.normLch(L,C,h), q = T.hslStage(L, n[0], T.transformHue(L,C,n[1]));   // whole chain before curves
          if (prev2!==null){ const d = ((q[2]-prev2+540)%360)-180; if (d < -1e-6) chf++; acc2 += d; }
          prev2 = q[2];
        }
        if (Math.abs(acc-360) > 1) hf++;
        if (Math.abs(acc2-360) > 1) chf++;
      }
      for (let L=0.3; L<=0.95; L+=0.05) for (let h=0; h<360; h+=3){ let pc=-1; for (let C=0.001; C<=0.34; C+=0.002){ const v = T.hslStage(L,C,h)[1]; if (v < pc-1e-9) cf++; pc = v; } }
      for (let L=0.3; L<=0.95; L+=0.05) for (let h=0; h<360; h+=3){ let pc=-1; for (let C=0.001; C<=0.34; C+=0.002){ const n = T.normLch(L,C,h), v = T.hslStage(L, n[0], T.transformHue(L,C,n[1]))[1]; if (v < pc-1e-9){ ccf++; ccd = Math.max(ccd, pc-v); } pc = v; } }
      for (let C=0.01; C<=0.3; C+=0.02) for (let h=1; h<360; h+=3){ let pl=-1; for (let L=0.02; L<=1; L+=0.005){ const v = T.hslStage(L,C,h)[0]; if (v < pl-1e-9) lf++; pl = v; } }
      for (let C=0.01; C<=0.3; C+=0.02) for (let h=1; h<360; h+=3){ let pl=-1; for (let L=0.02; L<=1; L+=0.005){ const n = T.normLch(L,C,h), v = T.hslStage(L, n[0], T.transformHue(L,C,n[1]))[0]; if (v < pl-1e-9) clf++; pl = v; } }
      const eff = ax => Array.from(T.HS[ax]).map(v => +v.toFixed(ax==='h' ? 1 : 3)).join(',');
      out.push('hsl '+name+' hueFolds='+hf+' chainFolds='+chf+' chromaFolds='+cf+' chainChromaFolds='+ccf+(ccf ? ' (max drop '+ccd.toExponential(1)+')' : '')+' lightFolds='+lf+' chainLightFolds='+clf+'  applied h['+eff('h')+'] s['+eff('s')+'] l['+eff('l')+']');
    }
    T.P.hsl = T.defaultHsl(); T.prepAll();
    // «Усреднение тонов»: whole chain (skin correction, chord, pins, «Цвета», averaging) along the hue circle, grid off the guard's grid.
    // fixedMoved — points at a kept hue (and ±9.9° around it) that moved at all (must be 0).
    const keepOf = a => Object.freeze([0,1,2,3,4,5,6,7].map(i => a.includes(i)));
    const acfgs = [
      ['one kept (orange) 100%', {}, null, [1], 100],
      ['one kept (blue) 100%, skin border', {}, null, [5], 100],
      ['one kept (blue) 1%', {}, null, [5], 1],
      ['two kept (orange, blue) 100%', {}, null, [1,5], 100],
      ['three kept (red, green, blue) 100%', {}, null, [0,3,5], 100],
      ['four kept (red, yellow, aqua, purple) 100%', {}, null, [0,2,4,6], 100],
      ['all eight kept 100%', {}, null, [0,1,2,3,4,5,6,7], 100],
      ['two kept + «Цвета» all + + chord + skin', { rotAll:45, skinCf:1.5, skinDh:15 }, sec(() => ({ h:30, s:100, l:100 })), [1,5], 100],
      ['one kept + «Цвета» alternating', {}, sec(i => i%2 ? { h:30, s:100, l:-100 } : { h:-30, s:-100, l:100 }), [2], 100],
      ['kept red by sample + split chord', { mode:'split', rotOpp:60, spread:30 }, sec(i => i===0 ? { h:30, s:-100, l:-100, ref:lipsRef, reach:0.5 } : i===5 ? { h:-30, s:100, l:100 } : {}), [0,5], 100],
      ['three kept + triad chord, skin −15°', { mode:'triad', rotAll:20, spread:-30, skinCf:0.5, skinDh:-15 }, null, [1,3,6], 100]];
    for (const [name, c, hsl, keep, amt] of acfgs){
      Object.assign(T.P, {mode:'pair',rotAll:0,rotOpp:0,spread:0,skinCf:1,skinDh:0}, c); T.P.hsl = hsl || T.defaultHsl();
      T.P.avgKeep = keepOf(keep); T.P.avgAmt = amt; T.prepAll();
      const chain = (L,C,h) => { const n = T.normLch(L,C,h); let q = [L, n[0], T.transformHue(L,C,n[1])]; if (T.HS.any) q = T.hslStage(q[0],q[1],q[2]); return T.avgStage(q[0],q[1],q[2]); };
      let f = 0, sf = 0, fixed = 0, moved = 0, maxMove = 0;
      for (let L=0.14; L<=0.98; L+=0.03) for (let C=0.011; C<=0.3; C+=0.007){
        let prev = null, acc = 0, prevS = null, accS = 0;
        for (let h=0; h<=360; h+=0.5){
          const v = chain(L,C,h)[2];
          if (prev!==null){ const d = ((v-prev+540)%360)-180; if (d < -1e-6) f++; acc += d; }
          prev = v;
          const w = T.avgStage(L,C,h)[2];   // the stage alone, on its own input
          if (prevS!==null){ const d = ((w-prevS+540)%360)-180; if (d < -1e-6) sf++; accS += d; }
          prevS = w; maxMove = Math.max(maxMove, Math.abs(w-h));
        }
        if (Math.abs(acc-360) > 1) f++;
        if (Math.abs(accS-360) > 1) sf++;
        for (const k of T.AV.keep) for (let o=-9.9; o<=9.9; o+=0.9){ const h = k.h+o, q = T.avgStage(L,C,h); fixed++; if (q[2] !== h || q[0] !== L || q[1] !== C) moved++; }
      }
      out.push('avg '+name+' chainFolds='+f+' stageFolds='+sf+' fixedMoved='+moved+'/'+fixed+'  applied '+Math.round(T.AV.s*100)+'% maxShift '+maxMove.toFixed(1)+'°');
    }
    T.P.avgKeep = keepOf([]); T.P.avgAmt = 0; T.P.hsl = T.defaultHsl(); T.prepAll();
    return out;
  });
  console.log(r.join('\n')); await b.close();
})();
