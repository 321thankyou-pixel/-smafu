const { chromium, devices } = require('/tmp/claude-0/-home-user/6a81b2d8-70c2-5f67-85ef-d0cc059993c0/scratchpad/pw/node_modules/playwright');
const URL = process.argv[2] || 'http://127.0.0.1:8765/index.html';
const results = [];
function rec(name, ok, detail) {
  results.push([name, ok]);
  console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  ' + detail : ''));
}
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  // iPhone 相当（タッチ・モバイル・DPR3）で、実HTTPサーバから読み込む
  const ctx = await browser.newContext({ ...devices['iPhone 13'] });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(600);

  rec('ページJSエラーなし', errors.length === 0, errors.join(' | '));
  rec('タッチ端末として認識', await page.evaluate(() => 'ontouchstart' in window));
  rec('① JS動作バッジ OK', (await page.textContent('#b1')) === 'OK');
  rec('② localStorage 利用可', (await page.textContent('#b2')) === 'OK');

  const chord = await page.getAttribute('.card.next', 'data-chord');
  const beforeForm = (await page.textContent('.card.next .form')).trim();
  const beforeDots = await page.$$eval('.card.next .dot', els => els.map(e => e.style.left).join(','));
  rec('次コードにフォーム登録あり (' + chord + ')', beforeForm !== '' && beforeForm !== 'フォーム未登録', beforeForm);
  rec('ダイアグラム描画あり', beforeDots.length > 0, beforeDots);
  // ドットが実寸を持つか（v11 の不具合: CSS に width/height が無く不可視だった）
  const dotBox = await page.$eval('.card.next .dot', e => {
    const r = e.getBoundingClientRect(); return r.width + 'x' + r.height;
  });
  rec('ドットが実際に見える大きさを持つ', !dotBox.startsWith('0x'), dotBox);

  // 実タップ
  await page.tap('.card.next');
  await page.waitForTimeout(400);
  rec('③ タップでシートが開く', (await page.getAttribute('#sheet', 'class')).includes('open'));
  const opts = await page.$$('#voiceOptions .vopt');
  rec('③ 候補が複数表示', opts.length >= 2, opts.length + '件');
  rec('③ バッジ b3 = OK', (await page.textContent('#b3')) === 'OK');

  const targetForm = (await opts[1].$eval('.vform', e => e.textContent)).trim();
  await opts[1].tap();
  await page.waitForTimeout(400);
  const afterForm = (await page.textContent('.card.next .form')).trim();
  const afterDots = await page.$$eval('.card.next .dot', els => els.map(e => e.style.left).join(','));
  rec('④ フォーム表記が即時変化', afterForm === targetForm && afterForm !== beforeForm, beforeForm + ' -> ' + afterForm);
  rec('④ ダイアグラムも変化', afterDots !== beforeDots, beforeDots + ' -> ' + afterDots);
  rec('④ バッジ b4 = OK', (await page.textContent('#b4')) === 'OK');

  const saved = await page.evaluate(c => localStorage.getItem('aliens.voicing.' + c), chord);
  rec('localStorage に保存', saved === '1', 'value=' + saved);

  await page.tap('#closeSheet');
  await page.waitForTimeout(300);
  rec('シートが閉じる', !(await page.getAttribute('#sheet', 'class')).includes('open'));
  rec('背景スクロールが復帰', (await page.evaluate(() => document.body.style.position)) === '');

  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(600);
  const reloadedForm = (await page.textContent('.card.next .form')).trim();
  rec('⑤ 再読み込み後も保持', reloadedForm === targetForm, reloadedForm + ' (期待 ' + targetForm + ')');
  rec('⑤ バッジ b5 = OK', (await page.textContent('#b5')) === 'OK');

  // 横スクロールが出ていないか（iPhone 幅）
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth);
  rec('横スクロールが発生しない', overflow <= 1, 'overflow=' + overflow);

  // タップ領域が44px以上か（iOS ヒューマンインターフェース目安）
  const tapSize = await page.$eval('.card.next', e => {
    const r = e.getBoundingClientRect(); return Math.round(r.width) + 'x' + Math.round(r.height);
  });
  rec('カードのタップ領域が十分', parseInt(tapSize.split('x')[1], 10) >= 44, tapSize);

  // 全フォームがパースできる
  const bad = await page.evaluate(() => {
    const v = window.__poc.voicings, bad = [];
    for (const c in v) for (const o of v[c])
      if (window.__poc.diagram(o.form).includes('フォーム表記エラー')) bad.push(c + ':' + o.form);
    return bad;
  });
  rec('全フォームがダイアグラム化可能', bad.length === 0, JSON.stringify(bad));

  await page.screenshot({ path: '/home/user/work/chromium_shot.png', fullPage: false });
  // シートを開いた状態のスクショも
  await page.tap('.card.next');
  await page.waitForTimeout(400);
  await page.screenshot({ path: '/home/user/work/chromium_sheet.png' });
  await browser.close();

  const ng = results.filter(r => !r[1]);
  console.log('\n===== Chromium(iPhone13 emulation) 結果: ' + (results.length - ng.length) + '/' + results.length + ' PASS =====');
  process.exit(ng.length ? 1 : 0);
})();
