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
    return out;
  });
  console.log(r.join('\n')); await b.close();
})();
