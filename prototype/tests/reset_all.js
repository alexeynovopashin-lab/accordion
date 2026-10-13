const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
  const p = await b.newPage({ viewport:{ width:1440, height:1200 } }); const errs=[]; p.on('pageerror', e=>errs.push(e.message));
  await p.goto('file://'+process.cwd()+'/complement_built.html'); await p.waitForTimeout(2500);
  const v = async () => [await p.$eval('#sRotAll', e=>e.value), await p.$eval('#oSkinCf', e=>e.textContent), await p.$eval('#oWb', e=>e.textContent), await p.$eval('#chips', e=>e.children.length)];
  await p.$eval('#sRotAll', e=>{ e.value=25; e.dispatchEvent(new Event('input')); e.dispatchEvent(new Event('change')); });
  await p.click('#skinToTarget'); console.log('edited', await v());
  await p.click('#resetAll'); await p.waitForTimeout(500); console.log('reset', await v(), await p.$eval('#status', e=>e.textContent));
  await p.click('#undo'); await p.waitForTimeout(500); console.log('undo', await v());
  console.log('ERR', errs); await b.close();
})();
