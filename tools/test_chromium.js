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

  // --- レビュー指摘の再発防止テスト ---

  // 指摘2: 開放弦を含むローコードはナットから描き、1F〜と表示する
  const nutInfo = await page.evaluate(() => {
    const h = window.__poc.diagram('x32000');
    return { nut: h.indexOf('dg nut') >= 0, from1: h.indexOf('>1F') >= 0 };
  });
  rec('開放弦のローコードにナットが出る (CM7 x32000)', nutInfo.nut && nutInfo.from1, JSON.stringify(nutInfo));

  // 指摘3: 5フレット窓に収まらないフォームはドットを窓外に描かずエラーにする
  const outOfWindow = await page.evaluate(() =>
    window.__poc.diagram('x-1-2-3-9-10').indexOf('フォーム表記エラー') >= 0);
  rec('窓外フォームはエラー表示になる', outOfWindow);

  // 指摘4: フォームを持たない N.C. をタップしても受入バッジ③を NG にしない
  await page.evaluate(() => window.__poc.openSheet('N.C.'));
  await page.waitForTimeout(200);
  const b3AfterNC = await page.textContent('#b3');
  rec('N.C. タップで③が NG にならない', b3AfterNC !== 'NG', 'b3=' + b3AfterNC);
  await page.evaluate(() => window.__poc.closeSheet());
  await page.waitForTimeout(200);

  // 指摘5: 第1候補(index 0)を選び直しても、再読み込み後に⑤が OK になる
  await page.tap('.card.next');
  await page.waitForTimeout(300);
  await (await page.$$('#voiceOptions .vopt'))[0].tap();
  await page.waitForTimeout(300);
  await page.tap('#closeSheet');
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(500);
  rec('index 0 を選び直しても⑤が OK', (await page.textContent('#b5')) === 'OK',
      (await page.textContent('#t5')).slice(0, 60));
  const zeroForm = (await page.textContent('.card.next .form')).trim();
  const zeroExpect = await page.evaluate(c => window.__poc.voicings[c][0].form,
    await page.getAttribute('.card.next', 'data-chord'));
  rec('index 0 の内容も正しく復元', zeroForm === zeroExpect, zeroForm);

  // 実機で見つかった不具合: 「次」カードのコード名が省略されていた
  const truncated = await page.evaluate(() => {
    var names = Object.keys(window.__poc.voicings).concat(['N.C.']);
    var el = document.querySelector('.card.next .chord');
    var bad = [];
    for (var i = 0; i < names.length; i++) {
      el.className = (names[i].length <= 4) ? 'chord'
        : (names[i].length <= 6) ? 'chord len1'
        : (names[i].length <= 9) ? 'chord len2' : 'chord len3';
      el.textContent = names[i];
      if (el.scrollWidth > el.clientWidth + 1) bad.push(names[i] + ' (' + el.scrollWidth + '>' + el.clientWidth + ')');
    }
    return bad;
  });
  rec('全コード名がカード内に省略なしで収まる', truncated.length === 0, JSON.stringify(truncated));
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(400);

  // --- 歌詞（端末内保存）のテスト。曲の実歌詞は使わずダミー文字列で検証する ---

  // 生成物に歌詞が埋め込まれていないこと（リポジトリに歌詞を残さない設計）
  const embedded = await page.evaluate(() => {
    var els = document.querySelectorAll('[data-mlyric]'), bad = [];
    for (var i = 0; i < els.length; i++) {
      if (els[i].textContent.trim() !== '') bad.push(i);
    }
    return { slots: els.length, filled: bad.length };
  });
  rec('初期状態の生成物に歌詞が埋め込まれていない',
      embedded.slots === 126 && embedded.filled === 0, JSON.stringify(embedded));

  // 小節番号つき書式の取り込み
  await page.fill('#lyricInput', 'M9 ダミー歌詞A\nM10 ダミー歌詞B\n11: ダミー歌詞C');
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  const numbered = await page.evaluate(() => [
    window.__poc.lyricOf(8), window.__poc.lyricOf(9), window.__poc.lyricOf(10)]);
  rec('小節番号つき書式を取り込める',
      numbered.join('|') === 'ダミー歌詞A|ダミー歌詞B|ダミー歌詞C', numbered.join('|'));
  rec('譜面の該当小節に歌詞が出る',
      (await page.textContent('[data-mlyric="8"]')).trim() === 'ダミー歌詞A');

  // 番号なし書式（開始小節から順に割り当て）
  await page.fill('#lyricInput', 'ダミー行1\n\nダミー行3');
  await page.fill('#lyricStart', '20');
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  const seq = await page.evaluate(() => [
    window.__poc.lyricOf(19), window.__poc.lyricOf(20), window.__poc.lyricOf(21)]);
  rec('番号なし書式を開始小節から順に割り当てる',
      seq[0] === 'ダミー行1' && seq[1] === '' && seq[2] === 'ダミー行3', JSON.stringify(seq));

  // 再読み込みしても歌詞が残る
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(500);
  rec('再読み込み後も歌詞が残る',
      (await page.evaluate(() => window.__poc.lyricOf(8))) === 'ダミー歌詞A');
  rec('歌詞の登録件数が表示される',
      (await page.textContent('#lyricStat')).indexOf('登録済み') >= 0,
      (await page.textContent('#lyricStat')).trim());

  // 小節をタップして1小節だけ直す
  await page.tap('.mini[data-mi="8"]');
  await page.waitForTimeout(300);
  rec('小節タップで歌詞編集シートが開く',
      (await page.textContent('#sheetTitle')).indexOf('M9') >= 0,
      await page.textContent('#sheetTitle'));
  rec('編集欄に既存の歌詞が入っている',
      (await page.inputValue('#lyricEdit')) === 'ダミー歌詞A');
  await page.fill('#lyricEdit', 'ダミー修正後');
  await page.tap('#lyricSaveOne');
  await page.waitForTimeout(300);
  rec('1小節だけ直せる',
      (await page.evaluate(() => window.__poc.lyricOf(8))) === 'ダミー修正後');

  // 書き出し
  await page.tap('#lyricExport');
  await page.waitForTimeout(200);
  const exported = await page.inputValue('#lyricInput');
  rec('書き出すと小節番号つきテキストになる',
      exported.indexOf('M9 ダミー修正後') === 0 && exported.indexOf('M20 ダミー行1') > 0,
      exported.split('\n')[0]);

  // 歌詞を消してもフォーム選択は残る
  await page.tap('#lyricClear');
  await page.waitForTimeout(300);
  rec('歌詞だけ消せる（フォーム選択は残る）',
      (await page.evaluate(() => window.__poc.lyricOf(8))) === '' &&
      (await page.textContent('#b5')) === 'OK');

  // 歌詞は外部に送信されない（fetch/XHR/beacon を一切使っていない）
  const src = await page.evaluate(() => document.documentElement.outerHTML);
  const net = ['fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', 'navigator.send']
    .filter(k => src.indexOf(k) >= 0);
  rec('ページに外部送信のコードが無い', net.length === 0, JSON.stringify(net));

  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(400);
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
