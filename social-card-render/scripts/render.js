/* CDP：按选择器逐个截图。由 render.py 调用。
   参数: <cdpPort> <url> <outDir> [vw] [vh] [scale] [selector]
   依赖 Node 22+ 的原生 WebSocket / fetch，不需要 puppeteer。 */
const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.argv[2] || '9333', 10);
const TARGET = process.argv[3];
const OUT = process.argv[4] || '.';
const VW = parseInt(process.argv[5] || '1080', 10);
const VH = parseInt(process.argv[6] || '1440', 10);
const SCALE = parseFloat(process.argv[7] || '2');
const SEL = process.argv[8] || '.card';

fs.mkdirSync(OUT, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));

class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map();
    ws.onmessage = ev => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) {
        const { res, rej } = this.pending.get(m.id);
        this.pending.delete(m.id);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
      }
    };
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((res, rej) => {
      this.pending.set(id, { res, rej });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
}

(async () => {
  const all = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
  const t = all.filter(x => x.type === 'page' && !x.url.startsWith('edge://'))[0];
  if (!t) { console.error('没有可用 page target'); process.exit(2); }
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  const cdp = new CDP(ws);

  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Emulation.setDeviceMetricsOverride',
    { width: VW, height: VH, deviceScaleFactor: 1, mobile: false });
  await cdp.send('Page.navigate', { url: TARGET });

  // 等 readyState 完成且所有 <img> 加载成功
  let ok = false;
  for (let i = 0; i < 40; i++) {
    await sleep(600);
    const r = await cdp.send('Runtime.evaluate', {
      expression: 'document.readyState + "|" + [...document.images].map(i=>i.complete&&i.naturalWidth>0?1:0).join("")',
      returnByValue: true,
    });
    const v = String(r.result.value);
    if (v.startsWith('complete') && !v.includes('0')) { console.log('ready:', v); ok = true; break; }
  }
  if (!ok) console.warn('警告：图片可能未全部加载完成，仍继续截图');

  const boxRes = await cdp.send('Runtime.evaluate', {
    expression: `JSON.stringify([...document.querySelectorAll(${JSON.stringify(SEL)})].map((el,i)=>{
      const r = el.getBoundingClientRect();
      return {id: el.id || ('card'+(i+1)), x: r.x + window.scrollX, y: r.y + window.scrollY,
              w: Math.round(r.width), h: Math.round(r.height)};
    }))`, returnByValue: true,
  });
  const cards = JSON.parse(boxRes.result.value);
  if (!cards.length) { console.error('选择器没匹配到元素:', SEL); process.exit(2); }

  for (const c of cards) {
    await sleep(400);
    const res = await cdp.send('Page.captureScreenshot', {
      format: 'png', captureBeyondViewport: true,
      clip: { x: c.x, y: c.y, width: c.w, height: c.h, scale: SCALE },
    });
    fs.writeFileSync(path.join(OUT, c.id + '.png'), Buffer.from(res.data, 'base64'));
    console.log(`  ${c.id}.png  ${c.w}x${c.h} -> ${Math.round(c.w * SCALE)}x${Math.round(c.h * SCALE)}`);
  }
  console.log('DONE 共', cards.length, '张');
  ws.close();
  process.exit(0);
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
