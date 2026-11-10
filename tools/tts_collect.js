const { chromium } = require('playwright-core');
const fs=require('fs'),path=require('path');
const SRC=path.resolve('index.html'), COL=path.resolve('_tts_col.html');
let s=fs.readFileSync(SRC,'utf8');
const a1='  Object.assign(GEN, YX_GEN);', a2='  const frName = k =>';
if(!s.includes(a1)||!s.includes(a2)){console.log('找不到注入點');process.exit(1);}
s=s.replace(a1,a1+'\n  window.__T = () => ({ GEN, ENG, st, age, startRound, setAge: v => { age = v; } });');
s=s.replace(a2,"  window.__T2 = () => ({ LEARN, EZL, EZ_EN, pkQ, PK_STK_TASK, FRIENDS, FR_BAD, PK_EN_NAME, PRAISE, EN_PRAISE, SLEEP: typeof SLEEP === 'undefined' ? [] : SLEEP, HEROES: typeof HEROES === 'undefined' ? [] : HEROES, SUBNAME: typeof SUBNAME === 'undefined' ? {} : SUBNAME, LS_TYPE: typeof LS_TYPE === 'undefined' ? {} : LS_TYPE, UI_SAY: typeof UI_SAY === 'undefined' ? null : UI_SAY, setAge: v => { age = v; } });\n"+a2);
fs.writeFileSync(COL,s);
(async()=>{
{const b=await chromium.launch(process.env.CHROME?{executablePath:process.env.CHROME}:{});const p=await (await b.newContext({viewport:{width:390,height:844}})).newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
await p.addInitScript(()=>{window.SPK=[];const ss={speaking:false,pending:false,getVoices:()=>[],cancel(){},speak(u){SPK.push([u.text,u.lang||'zh-TW']);setTimeout(()=>u.onend&&u.onend(),0);}};
 Object.defineProperty(window,'speechSynthesis',{value:ss});window.SpeechSynthesisUtterance=function(t){this.text=t};
 localStorage.setItem('ddn-nostat','1');localStorage.setItem('ddn-fe','0');localStorage.setItem('ddn-proLevel','3');localStorage.setItem('ddn-alwaysLearn','false');});
await p.goto('file://'+COL);await p.waitForTimeout(800);
const subs=await p.evaluate(()=>[...new Set([...document.querySelectorAll('.subject[data-sub]')].map(x=>x.dataset.sub))]);
console.log('subjects',subs.length);
const out=[];
for(const ag of ['small','big','six']) for(const sub of subs){
 const r=await p.evaluate(async([sub,ag,NN])=>{
  const T=window.__T(); try{localStorage.setItem('ddn-age',JSON.stringify(ag));localStorage.removeItem('ddn-adapt');}catch(e){} T.setAge(ag); const parts=[]; let err='';
  const add=sp=>(sp||[]).forEach(x=>{ if(Array.isArray(x)) parts.push([String(x[0]||''),x[1]||'zh-TW']); });
  try{ T.startRound(sub);}catch(e){err+='start:'+e.message;} T.setAge(ag);
  const T2=window.__T();
  for(let i=0;i<(T2.ENG[sub]?60:NN);i++){
   try{ const t=window.__T();
    if(t.ENG[sub]){ t.ENG[sub].render(); add(t.st&&t.st.q&&t.st.q.speech); }
    else if(t.GEN[sub]){ const q=t.GEN[sub](); add(q.speech); add(q.after); (q.options||[]).forEach(o=>o.label&&parts.push([o.label,o.lang||'zh-TW'])); if(q.practice) parts.push([q.practice,q.practiceLang||'zh-TW']); }
    else break;
   }catch(e){err=e.message;break;}
  }
  return {parts,err};
 },[sub,ag,+(process.env.N||2000)]);
 out.push([ag,sub,r.parts.length,r.err]); r.parts.forEach(x=>out.push(['P',x[0],x[1]]));
}
const spk=await p.evaluate(()=>SPK);
fs.writeFileSync('/tmp/tts_raw1.json',JSON.stringify({out,spk}));
console.log('errs',errs.slice(0,5));await b.close()}
{const b=await chromium.launch(process.env.CHROME?{executablePath:process.env.CHROME}:{});const p=await (await b.newContext({viewport:{width:390,height:844}})).newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
await p.addInitScript(()=>{const ss={speaking:false,pending:false,getVoices:()=>[],cancel(){},speak(u){setTimeout(()=>u.onend&&u.onend(),0);}};
 Object.defineProperty(window,'speechSynthesis',{value:ss});window.SpeechSynthesisUtterance=function(t){this.text=t};localStorage.setItem('ddn-nostat','1');localStorage.setItem('ddn-fe','0');});
await p.goto('file://'+COL);await p.waitForTimeout(800);
const R=await p.evaluate(()=>{
 const T=window.__T2(), out=[], add=(sp,who)=>(sp||[]).forEach(x=>Array.isArray(x)&&out.push([String(x[0]||''),x[1]||'zh-TW',x[2]||who||'']));
 const info={};
 for(const ag of ['small','big','six']){ T.setAge(ag); window.__T().setAge(ag);
  for(const k of Object.keys(T.LEARN)){ try{ const cs=T.LEARN[k](); cs.forEach(c=>add(c.say)); info[k]=cs.length;}catch(e){info[k]='ERR '+e.message;} }
  for(const lv of ['s','b','e','m','']){ try{localStorage.setItem('ddn-pkLvl',JSON.stringify(lv));}catch(e){} for(let i=0;i<300;i++){ try{ const q=T.pkQ(); add(q.say); }catch(e){info.pk='ERR '+e.message;break;} } }
 }
 T.EZL.forEach(c=>c.items.forEach(x=>add([[x.say||x.w,T.EZ_EN]])));
 T.PK_STK_TASK.forEach(t=>add([[t.say,t.en?'en-US':'zh-TW']]));
 Object.values(T.PK_EN_NAME).forEach(w=>add([[w,'en-US']]));
 T.FRIENDS.forEach(f=>add([[f[4](f[1])]],f[0]));
 T.FR_BAD.forEach(f=>{add([[f[4]]],f[0]); add([[f[5]]]);});
 (T.SLEEP||[]).forEach(st=>st.L.forEach(l=>add([[l[0],'zh-TW']],l[1]||'sleep'))); (T.HEROES||[]).forEach(h=>{h.P.forEach(pg=>add([[pg[2]]]));add([[h.Q[0]]]);h.Q[1].forEach(o=>add([[o]]));add([[h.say]],h.who==='en'?'':h.who);});
 if(T.LS_TYPE&&T.LS_TYPE.full){const tl=w=>add([[`你今天${w}，表現得真好！老師送你一張貼紙！`]],'tch');Object.keys(T.SUBNAME).forEach(k=>{tl(`${T.SUBNAME[k]}全部答對`);tl(`${T.SUBNAME[k]}進步好多`);});['streak','hero'].forEach(k=>tl(T.LS_TYPE[k][2]));Object.values(T.LS_TYPE).forEach(t=>add([[`${t[1]}，${t[2]}，好棒！`]]));}
 if(T.UI_SAY) add(T.UI_SAY());
 T.PRAISE.forEach(w=>add([[w]])); T.EN_PRAISE.forEach(w=>add([[w,'en-US']]));
 for(let c=65;c<91;c++) add([[String.fromCharCode(c)+'.','en-US']]);
 return {out,info};
});
fs.writeFileSync('/tmp/tts_raw2.json',JSON.stringify(R.out));
console.log(JSON.stringify(R.info).slice(0,1500));console.log('n',R.out.length,'errs',errs.slice(0,5));await b.close()}

{let s3=fs.readFileSync(SRC,'utf8');
 const h1="  async function speakOne(text, lang, my, who) {\n", h2='  const delay = ms => new Promise(r => setTimeout(r, ms));', h3="b.className = 'opt chunky'; b.id = 'opt' + i;";
 if(s3.includes(h1)&&s3.includes(h2)&&s3.includes(h3)){
 s3=s3.replace(h1,h1+"    { (window.__CAP=window.__CAP||[]).push([String(text).trim(),lang||'zh-TW',who||'']); return delay(1); }\n").replace(h2,'  const delay = ms => new Promise(r => setTimeout(r, Math.min(ms, 15)));').replace(h3,h3+" b.dataset.c = o.correct ? '1' : '0';");
 s3=s3.replace(a2,"  window.__C = () => ({ GEN, startRound, st: () => st });\n"+a2);
 fs.writeFileSync(COL,s3);
 const b=await chromium.launch(process.env.CHROME?{executablePath:process.env.CHROME}:{});const cap=new Map();
 for(const ag of ['small','big','six']){
  const p=await (await b.newContext({viewport:{width:390,height:844}})).newPage();
  await p.addInitScript(a=>{const ss={speaking:false,pending:false,getVoices:()=>[],cancel(){},speak(u){setTimeout(()=>u.onend&&u.onend(),0);}};Object.defineProperty(window,'speechSynthesis',{value:ss});window.SpeechSynthesisUtterance=function(t){this.text=t};
   localStorage.setItem('ddn-nostat','1');localStorage.setItem('ddn-limitMin','0');localStorage.setItem('ddn-alwaysLearn','false');localStorage.setItem('ddn-fe','0');localStorage.setItem('ddn-proLevel','3');localStorage.setItem('ddn-age',JSON.stringify(a));},ag);
  await p.goto('file://'+COL);await p.waitForTimeout(800);
  const subs=await p.evaluate(()=>[...new Set([...document.querySelectorAll('.subject[data-sub]')].map(x=>x.dataset.sub))].concat(['place','review']));
  for(const sub of subs){
   for(let r=0;r<2;r++){
    await p.evaluate(s=>{document.querySelectorAll('.ls-ov,.move-box').forEach(e=>e.remove());try{window.__C().startRound(s);}catch(e){}},sub);
    for(let k=0;k<500;k++){await p.waitForTimeout(15);
     const d=await p.evaluate(r=>{const st=window.__C().st();if(!document.getElementById('done').hidden)return 'done';if(document.getElementById('game').hidden)return 'gone';const box=document.getElementById('options');if(!box||box.classList.contains('waiting')||st.locked)return 'w';const en=[...box.children].filter(o=>!o.disabled&&!o.classList.contains('gone'));if(!en.length)return 'n';const want=(st.i===0||(r&&st.i===2))?'0':'1';(en.find(o=>o.dataset.c===want)||en[0]).click();return 'x';},r);
     if(d==='done'||d==='gone')break;}
    await p.waitForTimeout(120);
   }
   // 多看幾題的第一題，收更多題目
   for(let r=0;r<+(process.env.N3||40);r++){await p.evaluate(s=>{try{window.__C().startRound(s);}catch(e){}},sub);await p.waitForTimeout(20);}
  }
  (await p.evaluate(()=>window.__CAP||[])).forEach(x=>cap.set(x.join('\u0001'),x));
  await p.close();
 }
 fs.writeFileSync('/tmp/tts_raw3.json',JSON.stringify([...cap.values()]));console.log('crawl',cap.size);await b.close();}
 else console.log('第三段找不到注入點，略過');}
fs.unlinkSync(COL);
})();
