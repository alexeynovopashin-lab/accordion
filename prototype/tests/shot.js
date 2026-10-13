const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) }).catch(()=>chromium.launch());
  const p = await b.newPage({ viewport:{ width:1440, height:1500 } });
  const errs=[]; p.on('pageerror', e=>errs.push(e.message)); p.on('console', m=>{ if(m.type()==='error') errs.push(m.text()); });
  await p.goto('file://'+process.cwd()+'/complement_built.html');
  await p.waitForTimeout(2500);
  const txt = id => p.$eval('#'+id, e=>e.innerText).catch(()=>'?');
  for (const id of ['status','chips','wbInfo','skinInfo','wbOnly','lBlack','lGrey','lWhite','pinInfo','rSkin','rMass']) console.log(id+':', (await txt(id)).replace(/\n/g,' | '));
  await p.screenshot({ path:'shot1.png', fullPage:true });
  await p.click('#skinToTarget'); await p.waitForTimeout(1500);
  for (const id of ['skinInfo','oSkinCf','oSkinDh','pinInfo']) console.log('after target', id+':', (await txt(id)).replace(/\n/g,' | '));
  // rotate chord to test pins
  await p.$eval('#sRotAll', e=>{ e.value=30; e.dispatchEvent(new Event('input')); }); await p.waitForTimeout(1200);
  console.log('rot30 pinInfo:', (await txt('pinInfo')).replace(/\n/g,' | '));
  await p.screenshot({ path:'shot2.png', fullPage:true });
  console.log('ERRORS:', errs);
  await b.close();
})();
