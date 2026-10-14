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
  // desktop shell: page does not scroll, tool column scrolls on its own, folding/scrolling tools never moves or rescales the photo
  let fails = 0; const ok = (name, cond, info) => { console.log((cond ? 'PASS ' : 'FAIL ')+name+(info ? '  '+info : '')); if (!cond) fails++; };
  const rect = () => p.$eval('#img', e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map(v => +v.toFixed(2)); });
  const pg = () => p.evaluate(() => ({ top:(document.scrollingElement||document.documentElement).scrollTop, bodyTop:document.body.scrollTop,
    docH:document.documentElement.scrollHeight, winH:innerHeight, tools:document.querySelector('.tools').scrollTop,
    toolsMax:document.querySelector('.tools').scrollHeight-document.querySelector('.tools').clientHeight, zv:document.getElementById('zVal').textContent }));
  await p.click('#zFit'); await p.waitForTimeout(300);
  const r0 = await rect(), g0 = await pg();
  ok('shell: page does not scroll (scrollTop 0, scrollHeight = window)', g0.top === 0 && g0.bodyTop === 0 && g0.docH === g0.winH, JSON.stringify(g0));
  ok('shell: tool column is longer than the window (it has something to scroll)', g0.toolsMax > 300, 'toolsMax='+g0.toolsMax);
  await p.$eval('.tools', e => { e.scrollTop = e.scrollHeight; }); await p.waitForTimeout(150);
  const r1 = await rect(), g1 = await pg();
  ok('shell: tools scrolled to the bottom, photo frame unchanged', JSON.stringify(r0) === JSON.stringify(r1) && g1.tools === g1.toolsMax && g1.top === 0 && g1.zv === g0.zv, 'before '+r0+' after '+r1+' tools='+g1.tools+'/'+g1.toolsMax);
  const side = await p.$eval('.side', e => { const r = e.getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2]; });
  await p.$eval('.tools', e => { e.scrollTop = 0; }); await p.mouse.move(side[0], side[1]); await p.mouse.wheel(0, 700); await p.waitForTimeout(150);
  const g2 = await pg();
  ok('shell: wheel over the tool column scrolls the column, not the photo or the page', g2.tools > 0 && g2.top === 0 && JSON.stringify(await rect()) === JSON.stringify(r0) && g2.zv === g0.zv, 'tools='+g2.tools);
  await p.$eval('.tools', e => { e.scrollTop = 0; });
  const heads = ['Свет и кожа', 'Кривая', 'Движение', 'Что держать'];
  for (const h of heads) await p.click(`h2:has-text("${h}")`);
  await p.waitForTimeout(150);
  const r2 = await rect(), g3 = await pg();
  ok('shell: opening/closing plates does not move or rescale the photo', JSON.stringify(r0) === JSON.stringify(r2) && g3.zv === g0.zv, 'after '+r2);
  for (const h of heads) await p.click(`h2:has-text("${h}")`);
  await p.setViewportSize({ width:1280, height:760 }); await p.waitForTimeout(400);
  const rb = await p.$eval('.canvas-box', e => { const r = e.getBoundingClientRect(); return [r.width, r.height]; }), ri = await rect();
  ok('shell: after the window shrinks "fit" shows the whole frame', ri[2] <= rb[0]+0.5 && ri[3] <= rb[1]+0.5 && (Math.abs(ri[2]-rb[0]) < 1.5 || Math.abs(ri[3]-rb[1]) < 1.5), 'box '+rb.map(Math.round)+' img '+ri.slice(2));
  console.log('ERRORS', errs); await b.close();
  if (fails || errs.length) process.exit(1);
})();
