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
    return out;
  });
  console.log(r.join('\n')); await b.close();
})();
