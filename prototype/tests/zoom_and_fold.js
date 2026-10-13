const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ ...(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}) });
  const p = await b.newPage({ viewport:{ width:1440, height:1000 } });
  const errs=[]; p.on('pageerror', e=>errs.push(e.message)); p.on('console', m=>{ if(m.type()==='error') errs.push(m.text()); });
  await p.goto('file://'+process.cwd()+'/complement_built.html'); await p.waitForTimeout(2500);
  const info = () => p.evaluate(()=>{const c=document.getElementById('img'),r=c.getBoundingClientRect(),b=document.querySelector('.canvas-box');return {w:Math.round(r.width),h:Math.round(r.height),cw:c.width,ch:c.height,sl:b.scrollLeft,st:b.scrollTop,bw:b.clientWidth,bh:b.clientHeight,zv:document.getElementById('zVal').textContent}});
  console.log('fit', await info());
  const r = await p.$eval('#img', e=>{const r=e.getBoundingClientRect();return {x:r.left,y:r.top,w:r.width,h:r.height}});
  // wheel zoom at the image centre point
  const cx=r.x+r.w*0.5, cy=r.y+r.h*0.3;
  const probe = async (px,py)=> p.evaluate(([px,py])=>{const c=document.getElementById('img'),r=c.getBoundingClientRect();return [Math.floor((px-r.left)/r.width*c.width),Math.floor((py-r.top)/r.height*c.height)]},[px,py]);
  console.log('canvas pt before', await probe(cx,cy));
  await p.mouse.move(cx,cy); await p.mouse.wheel(0,-600); await p.waitForTimeout(300);
  console.log('after wheel', await info(), 'canvas pt under cursor', await probe(cx,cy));
  await p.click('#zOne'); await p.waitForTimeout(200); console.log('1:1', await info());
  // pan by drag
  const before = await info();
  await p.mouse.move(cx,cy); await p.mouse.down(); await p.mouse.move(cx-80,cy-60,{steps:5}); await p.mouse.up();
  console.log('pan', before.sl, before.st, '->', (await info()).sl, (await info()).st);
  const nm = await p.evaluate(()=>document.querySelectorAll('.chip').length);
  await p.click('#pSky'); const cnt0 = await p.evaluate(()=>document.querySelectorAll('.chip').length);
  await p.mouse.move(cx,cy); await p.mouse.down(); await p.mouse.move(cx-30,cy-30,{steps:4}); await p.mouse.up();
  console.log('chips after drag (should stay):', cnt0, await p.evaluate(()=>document.querySelectorAll('.chip').length));
  await p.click('#zFit'); await p.waitForTimeout(300); console.log('fit again', await info());
  await p.screenshot({path:'z1.png'});
  // folding
  await p.click('h2:has-text("Круг ·")'); 
  const f = await p.evaluate(()=>[...document.querySelectorAll('.panel')].map(x=>x.classList.contains('collapsed')));
  console.log('collapsed flags', f);
  await p.click('#foldAll'); await p.screenshot({path:'z2.png'});
  console.log('all collapsed', await p.evaluate(()=>[...document.querySelectorAll('.panel')].every(x=>x.classList.contains('collapsed'))));
  await p.click('#unfoldAll'); await p.waitForTimeout(400);
  console.log('wheel size after unfold', await p.$eval('#wheel',e=>e.width));
  console.log('ERRORS', errs); await b.close();
})();
