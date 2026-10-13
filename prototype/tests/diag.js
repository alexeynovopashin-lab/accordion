const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
  const p = await b.newPage();
  await p.goto('file://'+process.cwd()+'/test_built.html'); await p.waitForTimeout(2500);
  console.log(await p.evaluate(() => {
    const T = window.__t, out=[];
    for (const [c,lock] of [[{mode:'split',rotOpp:60,spread:30},false],[{mode:'split',rotOpp:60,spread:30},true],[{rotAll:-60,skinCf:1.5,skinDh:15},false],[{rotAll:-60},true],[{rotAll:-60,skinDh:15},true]]){
      Object.assign(T.P,{mode:'pair',rotAll:0,rotOpp:0,spread:0,skinCf:1,skinDh:0,skinLock:lock},c); T.prepAll();
      let folds=0, ex=null;
      for (let L=0.2; L<=0.98; L+=0.04) for (let C=0.01; C<=0.3; C+=0.01){ let prev=null;
        for (let h=0; h<=360; h+=0.5){ const n=T.normLch(L,C,h); const nh=T.transformHue(L,C,n[1]);
          if (prev!==null){ const d=((nh-prev+540)%360)-180; if (d<-1e-6){ folds++; if(!ex) ex={L:L.toFixed(2),C:C.toFixed(2),h,d:d.toFixed(3)}; } } prev=nh; } }
      out.push(JSON.stringify(c)+' lock='+lock+' folds='+folds+' ex='+JSON.stringify(ex)+' pins='+T.PINS.map(p=>p.type+':'+p.h.toFixed(0)+'/w'+p.w.toFixed(1)+'/FK'+p.FK.toFixed(0)).join(' ')+' skin='+(T.NM.skin?T.NM.skin.h.toFixed(0)+'/w'+T.NM.skin.w.toFixed(1)+'/FK'+T.NM.skin.FK.toFixed(0):'-'));
    }
    return out.join('\n');
  })); await b.close();
})();
