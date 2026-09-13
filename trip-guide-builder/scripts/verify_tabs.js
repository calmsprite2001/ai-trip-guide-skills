// 旅行攻略 · 多 Tab 渲染验证（CDP 直连，Node 22+ 原生 WebSocket，无需 puppeteer）
//
// 用法：
//   1) 起本地服务：  python -m http.server 8901 --directory <publish目录>
//   2) 起 Edge：     msedge --headless=new --disable-gpu --disable-sync --no-first-run \
//                          --user-data-dir=%TEMP%\edgeshot --remote-debugging-port=9333 about:blank
//   3) 跑：          node verify_tabs.js "http://127.0.0.1:8901/index.html"
//
// ⚠️ 启动 Edge 必须给 about:blank，否则首次运行的同步确认弹窗会抢走 page target，
//    你会拿到 edge:// 页面并以为"页面坏了"。必须带 --disable-sync。

const fs = require('fs');
const PORT = process.env.CDP_PORT || 9333;
const BASE = process.argv[2] || 'http://127.0.0.1:8901/index.html';
const SHOT = process.argv[3] || null;
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function main() {
  // ---- 找 target ----
  let target = null;
  for (let i = 0; i < 60; i++) {
    try {
      const all = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
      const pages = all.filter(t => t.type === 'page' && t.webSocketDebuggerUrl);
      if (pages.length) {
        target = pages.find(t => !t.url.startsWith('edge://')) || pages[0];
        break;
      }
    } catch (e) {}
    await sleep(300);
  }
  if (!target) { console.log('NO_TARGET  (Edge 没起来？或端口被占)'); process.exit(1); }

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 0; const pend = new Map();
  const send = (m, p = {}) => new Promise(r => {
    const i = ++id; pend.set(i, r);
    ws.send(JSON.stringify({ id: i, method: m, params: p }));
  });
  ws.addEventListener('message', ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
  });
  await new Promise(r => ws.addEventListener('open', r));

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  // 唯一能拿到精确 CSS 视口的方式（--window-size 会被 Windows 缩放污染）
  await send('Emulation.setDeviceMetricsOverride',
             { width: 390, height: 1500, deviceScaleFactor: 1, mobile: true });

  const reqs = [];
  ws.addEventListener('message', ev => {
    const m = JSON.parse(ev.data);
    if (m.method === 'Network.requestWillBeSent') reqs.push(m.params.request.url);
  });

  console.log('navigate ->', BASE);
  await send('Page.navigate', { url: BASE });
  await sleep(7000);

  const j = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
    if (r.result && r.result.exceptionDetails) return 'JS_ERR:' + r.result.exceptionDetails.text;
    return r.result && r.result.result ? r.result.result.value : null;
  };

  // ---- 页面自检 ----
  console.log('\n== 页面自检 ==');
  console.log('视口        =', await j(`document.documentElement.clientWidth + ' x ' + window.innerHeight`));
  console.log('横向溢出    =', await j(
    `(function(){var vw=document.documentElement.clientWidth,out=[];` +
    `function inScroller(el){var p=el.parentElement;` +
    `while(p&&p!==document.body){var ov=getComputedStyle(p).overflowX;` +
    `if(ov==='auto'||ov==='scroll')return true;p=p.parentElement;}return false;}` +
    `document.querySelectorAll('body *').forEach(function(el){var r=el.getBoundingClientRect();` +
    `if(r.width>0&&r.right>vw+1&&!inScroller(el)){var c=(el.className&&el.className.toString())||'';` +
    `out.push(el.tagName.toLowerCase()+(c?'.'+c.split(' ')[0]:'')+'[w'+Math.round(r.width)+',r'+Math.round(r.right)+']');}});` +
    `return out.length? out.slice(0,12).join(' ~ ') : 'NONE (横向滚动容器内的子项已排除)';})()`));
  console.log('undefined   =', await j(
    `(function(){var t=document.body.innerText;var m=t.match(/undefined/g);return m?m.length+' 处':'0';})()`));

  // ---- 枚举所有 Tab ----
  const tabs = await j(`JSON.stringify(Array.from(document.querySelectorAll('#nav button')).map(function(b){return b.getAttribute('data-id')}))`);
  if (!tabs) { console.log('\n!! 没找到 #nav button，检查选择器'); ws.close(); process.exit(1); }
  const ids = JSON.parse(tabs);
  console.log('\n== 逐个 Tab 验证（共 %d 个）==', ids.length);

  const rep = await j(`JSON.stringify((function(){
    var out=[];
    ${JSON.stringify(ids)}.forEach(function(id){
      var b=document.querySelector('#nav button[data-id="'+id+'"]');
      if(!b){ out.push(id+' => NO_BUTTON'); return; }
      b.click();
      var hi=document.getElementById('heroImg');
      var ht=document.getElementById('heroTitle');
      var on=Array.from(document.querySelectorAll('.page')).filter(function(p){return p.classList.contains('on')}).map(function(p){return p.id}).join(',');
      out.push([id, hi?hi.getAttribute('src'):'-', ht?ht.textContent.trim():'-', on].join(' | '));
    });
    return out;
  })())`);

  const rows = String(rep).split('","').join('\n').replace(/^\[?"|"\]?$/g, '');
  console.log(rows);

  // ---- 封面切换是否真的生效 ----
  const srcs = String(rep).match(/img\/[^"|]+/g) || [];
  const uniq = Array.from(new Set(srcs));
  console.log('\n用到的封面图 %d 张: %s', uniq.length, uniq.join(', '));
  if (uniq.length <= 1 && ids.length > 2) {
    console.log('!! 所有 Tab 共用同一张封面 —— 顶部封面很可能没有随城市切换（常见 bug）');
  }

  // ---- 图片加载 ----
  const imgs = await j(`JSON.stringify(Array.from(document.querySelectorAll('.page.on img')).map(function(i){return [i.getAttribute('src'), i.naturalWidth];}))`);
  console.log('当前页图片  =', imgs);
  console.log('图片请求    =', JSON.stringify(reqs.filter(u => /\.(jpg|jpeg|png|webp)/i.test(u)).map(u => u.split('/').slice(-2).join('/'))));

  // ---- 截图 ----
  if (SHOT) {
    const shot = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(SHOT, Buffer.from(shot.result.data, 'base64'));
    console.log('\nsaved', SHOT, fs.statSync(SHOT).size, 'bytes');
  }

  ws.close();
  process.exit(0);
}
main().catch(e => { console.error('ERR', e); process.exit(1); });
