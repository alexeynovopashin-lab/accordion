const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
  const p = await b.newPage({ viewport:{ width:1440, height:1100 } });
  await p.goto('file://'+process.cwd()+'/complement_built.html'); await p.waitForTimeout(2500);
  await p.click('#pNeutral');
  const box = await p.$eval('#img', e => { const r=e.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height}; });
  await p.mouse.click(box.x+box.w*(103/1717), box.y+box.h*(1932/2576)); await p.waitForTimeout(1500);
  console.log('status:', await p.$eval('#status', e=>e.innerText));
  console.log('wbInfo:', (await p.$eval('#wbInfo', e=>e.innerText)).replace(/\n/g,' | '));
  console.log('skin:', (await p.$eval('#skinInfo', e=>e.innerText)).replace(/\n/g,' | '));
  await p.click('#tClouds'); await p.waitForTimeout(800);
  await p.screenshot({ path:'shot3.png', clip:{x:0,y:0,width:1440,height:1100} });
  const m = await b.newPage({ viewport:{ width:390, height:800 } });
  await m.goto('file://'+process.cwd()+'/complement_built.html'); await m.waitForTimeout(2500);
  console.log('mobile overflow:', await m.evaluate(()=>document.documentElement.scrollWidth - innerWidth));
  await b.close();
})();
