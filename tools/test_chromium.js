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
      (await page.inputValue('.lfield[data-b="0"]')) === 'ダミー歌詞A');
  rec('拍ごとの入力欄が拍数ぶん出る',
      (await page.$$('#voiceOptions .lfield')).length === 4,
      String((await page.$$('#voiceOptions .lfield')).length));
  await page.fill('.lfield[data-b="0"]', 'ダミー修正後');
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

  // --- 演奏設定（チューニング・カポ・表記・テンポ） ---

  // 実音表記が U-FRET の原曲キー表記と一致すること（半音下げ・カポなし = -1）
  const tp = await page.evaluate(() => {
    const t = window.__poc.transposeName;
    return {
      'CM7': t('CM7', -1), 'D/C': t('D/C', -1), 'Bm7': t('Bm7', -1),
      'Em7': t('Em7', -1), 'F#m7': t('F#m7', -1), 'GM7': t('GM7', -1),
      'C#m7-5': t('C#m7-5', -1), 'F#7': t('F#7', -1), 'E7': t('E7', -1),
      'B7': t('B7', -1), 'Am7': t('Am7', -1), 'A7': t('A7', -1),
      'Dm7': t('Dm7', -1), 'N.C.': t('N.C.', -1), 'F#(b9)/Bb': t('F#(b9)/Bb', -1),
      'Baug7(b9)': t('Baug7(b9)', -1)
    };
  });
  const want = { 'CM7':'BM7','D/C':'Db/B','Bm7':'Bbm7','Em7':'Ebm7','F#m7':'Fm7','GM7':'GbM7',
    'C#m7-5':'Cm7-5','F#7':'F7','E7':'Eb7','B7':'Bb7','Am7':'Abm7','A7':'Ab7','Dm7':'Dbm7',
    'N.C.':'N.C.','F#(b9)/Bb':'F(b9)/A','Baug7(b9)':'Bbaug7(b9)' };
  const tpBad = Object.keys(want).filter(k => tp[k] !== want[k]).map(k => k + ':' + tp[k]);
  rec('実音表記が原曲キー表記と一致する', tpBad.length === 0, JSON.stringify(tpBad));

  // 表記切替がカードと譜面に反映される
  await page.tap('#segView button[data-v="sound"]');
  await page.waitForTimeout(300);
  rec('実音表記に切り替わる（カード）',
      (await page.textContent('.card.current .chord')).trim() === 'BM7',
      await page.textContent('.card.current .chord'));
  rec('実音表記に切り替わる（譜面）',
      (await page.textContent('.mc[data-c="CM7"]')).indexOf('BM7') === 0,
      (await page.textContent('.mc[data-c="CM7"]')).trim());
  // 表記を変えてもフォーム辞書は元のコード名で引ける
  await page.tap('.card.next');
  await page.waitForTimeout(300);
  rec('実音表記でもフォーム候補が出る',
      (await page.$$('#voiceOptions .vopt')).length >= 2);
  await page.tap('#closeSheet');
  await page.waitForTimeout(200);

  // キー判定
  rec('半音下げ・カポなしで原曲キーと一致と表示',
      (await page.textContent('#keyBox')).indexOf('原曲キーと一致') >= 0);
  await page.tap('#segTune button[data-v="0"]');
  await page.waitForTimeout(300);
  rec('レギュラーにすると原曲より高いと表示',
      (await page.textContent('#keyBox')).indexOf('原曲より') >= 0,
      (await page.textContent('#keyBox')).slice(0, 60).replace(/\s+/g, ' '));
  await page.tap('#segTune button[data-v="-1"]');
  await page.waitForTimeout(300);

  // カポ
  await page.fill('#capo', '2');
  await page.dispatchEvent('#capo', 'change');
  await page.waitForTimeout(300);
  rec('カポがヘッダーに出る', (await page.textContent('#meta')).indexOf('カポ2F') >= 0,
      await page.textContent('#meta'));
  await page.fill('#capo', '0');
  await page.dispatchEvent('#capo', 'change');
  await page.waitForTimeout(300);

  // テンポ
  await page.fill('#bpm', '100');
  await page.dispatchEvent('#bpm', 'change');
  await page.waitForTimeout(300);
  rec('テンポ変更がヘッダーに出る', (await page.textContent('#meta')).indexOf('BPM 100') >= 0,
      await page.textContent('#meta'));

  // 設定が再読み込み後も残る
  await page.tap('#segView button[data-v="sound"]');
  await page.waitForTimeout(200);
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(500);
  const kept = await page.evaluate(() => window.__poc.settings);
  rec('設定が再読み込み後も残る', kept.bpm === 100 && kept.view === 'sound', JSON.stringify(kept));
  await page.tap('#segView button[data-v="shape"]');
  await page.fill('#bpm', '85');
  await page.dispatchEvent('#bpm', 'change');
  await page.waitForTimeout(300);

  // --- レビュー指摘1〜5の再発防止 ---

  await page.tap('#lyricClear');
  await page.waitForTimeout(300);

  // 指摘1: 空行でその小節の歌詞が消える
  await page.fill('#lyricStart', '30');
  await page.fill('#lyricInput', 'ダミーあ\nダミーい\nダミーう');
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  await page.fill('#lyricStart', '30');
  await page.fill('#lyricInput', 'ダミーあ\n\nダミーう');
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  rec('空行で既存の歌詞を消せる',
      (await page.evaluate(() => window.__poc.lyricOf(30))) === '',
      JSON.stringify(await page.evaluate(() => [
        window.__poc.lyricOf(29), window.__poc.lyricOf(30), window.__poc.lyricOf(31)])));

  // 指摘2: 書き出す → 取り込む の往復で失われない（改行入りも含む）
  await page.tap('#lyricClear');
  await page.waitForTimeout(200);
  await page.evaluate(() => window.__poc.openLyricSheet(8));
  await page.waitForTimeout(300);
  await page.fill('.lfield[data-b="0"]', 'ダミー1行目\nダミー2行目');
  await page.tap('#lyricSaveOne');
  await page.waitForTimeout(300);
  await page.fill('#lyricInput', 'M11 ダミーさんばんめ');
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  const before = await page.evaluate(() => JSON.stringify(window.__poc.lyrics));
  await page.tap('#lyricExport');
  await page.waitForTimeout(200);
  const backup = await page.inputValue('#lyricInput');
  await page.tap('#lyricClear');
  await page.waitForTimeout(200);
  await page.fill('#lyricInput', backup);
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  const after = await page.evaluate(() => JSON.stringify(window.__poc.lyrics));
  rec('書き出し→取り込みの往復で歌詞が失われない', before === after,
      'before=' + before + ' after=' + after);

  // 指摘3: 「数字＋半角スペース」で始まる行を小節番号と誤認しない
  const heur = await page.evaluate(() =>
    window.__poc.parseLyricText('1 ダミー\n2 ダミー\n3 ダミー\n4 ダミー\n5 ダミー', 9));
  rec('数字＋半角スペースの行を番号と誤認しない',
      heur.mode === 'sequential' && heur.map['8.0'] === '1 ダミー',
      heur.mode + ' / ' + heur.map['8.0']);

  // 指摘4: 保存できなかったときに画面で知らせる
  const quota = await page.evaluate(() => {
    var orig = Storage.prototype.setItem;
    Storage.prototype.setItem = function(k, v){
      if (String(k).indexOf('aliens.lyrics') === 0) { throw new Error('QuotaExceeded'); }
      return orig.call(this, k, v);
    };
    var r = window.__poc.store.set('aliens.lyrics.v1', '{}');
    Storage.prototype.setItem = orig;
    return r;
  });
  rec('保存失敗を store.set が返す', quota === false, String(quota));

  // 指摘5: 壊れた保存値を復元しない
  const guard = await page.evaluate(() => {
    var n = window.__poc.measures.length;
    return { arr: JSON.stringify(['a','b']), over: JSON.stringify({ '999': 'x' }), n: n };
  });
  await page.evaluate(v => localStorage.setItem('aliens.lyrics.v1', v), guard.arr);
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(400);
  rec('配列が保存されていても復元しない',
      (await page.evaluate(() => JSON.stringify(window.__poc.lyrics))) === '{}');
  await page.evaluate(v => localStorage.setItem('aliens.lyrics.v1', v), guard.over);
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(400);
  rec('範囲外の小節番号を復元しない',
      (await page.evaluate(() => JSON.stringify(window.__poc.lyrics))) === '{}');

  // 保存を消す は歌詞を消さない / 歌詞を全部消す はフォーム選択を消さない
  await page.fill('#lyricInput', 'M9 ダミー分離テスト');
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  await page.tap('#btnClear');
  await page.waitForTimeout(600);
  rec('「保存を消す」で歌詞は消えない',
      (await page.evaluate(() => window.__poc.lyricOf(8))) === 'ダミー分離テスト');

  await page.tap('#lyricClear');
  await page.waitForTimeout(300);

  // --- 拍単位の位置合わせ ---
  await page.tap('#lyricClear');
  await page.waitForTimeout(300);

  // 「小節.拍」書式で拍を指定して取り込める
  await page.fill('#lyricInput', 'M9 ダミーあ\nM9.3 ダミーい\nM10.4 ダミーう');
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  rec('小節.拍 書式で拍を指定できる',
      (await page.evaluate(() => JSON.stringify(window.__poc.lyrics)))
        === '{"8.0":"ダミーあ","8.2":"ダミーい","9.3":"ダミーう"}',
      await page.evaluate(() => JSON.stringify(window.__poc.lyrics)));

  // 書き出し→取り込みで拍位置が保たれる
  const beatBefore = await page.evaluate(() => JSON.stringify(window.__poc.lyrics));
  await page.tap('#lyricExport');
  await page.waitForTimeout(200);
  const beatBackup = await page.inputValue('#lyricInput');
  await page.tap('#lyricClear');
  await page.waitForTimeout(200);
  await page.fill('#lyricInput', beatBackup);
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  rec('書き出し→取り込みで拍位置が保たれる',
      (await page.evaluate(() => JSON.stringify(window.__poc.lyrics))) === beatBefore,
      beatBackup.replace(/\n/g, ' | '));

  // 譜面が拍のマス目で歌詞を表示する
  rec('譜面が拍のマス目で表示する',
      (await page.$$('[data-mlyric="8"] .mlb')).length === 4,
      String((await page.$$('[data-mlyric="8"] .mlb')).length));

  // ← → で1拍ずつ動かせる
  await page.evaluate(() => window.__poc.openLyricSheet(8));
  await page.waitForTimeout(300);
  await page.tap('.lnudge[data-b="2"][data-d="1"]');
  await page.waitForTimeout(400);
  rec('→ で1拍うしろへ動く',
      (await page.evaluate(() => window.__poc.lyrics['8.3'])) === 'ダミーい'
      && (await page.evaluate(() => window.__poc.lyrics['8.2'])) === undefined,
      await page.evaluate(() => JSON.stringify(window.__poc.lyrics)));

  // 小節をまたいで動く
  await page.tap('.lnudge[data-b="3"][data-d="1"]');
  await page.waitForTimeout(400);
  rec('小節をまたいで動く',
      (await page.evaluate(() => window.__poc.lyrics['9.0'])) === 'ダミーい',
      await page.evaluate(() => JSON.stringify(window.__poc.lyrics)));
  rec('動かした先の小節にシートが移る',
      (await page.textContent('#sheetTitle')).indexOf('M10') === 0,
      await page.textContent('#sheetTitle'));

  // 移動先が埋まっていれば動かさない
  await page.evaluate(() => window.__poc.closeSheet());
  await page.waitForTimeout(200);
  const blocked = await page.evaluate(() => {
    window.__poc.lyrics['9.1'] = 'ダミー壁';
    return window.__poc.shiftFragment ? 'n/a' : 'n/a';
  });
  await page.evaluate(() => window.__poc.openLyricSheet(9));
  await page.waitForTimeout(300);
  await page.tap('.lnudge[data-b="0"][data-d="1"]');
  await page.waitForTimeout(400);
  rec('移動先が埋まっていれば動かさない',
      (await page.evaluate(() => window.__poc.lyrics['9.0'])) === 'ダミーい'
      && (await page.evaluate(() => window.__poc.lyrics['9.1'])) === 'ダミー壁',
      await page.evaluate(() => JSON.stringify(window.__poc.lyrics)));
  await page.evaluate(() => window.__poc.closeSheet());
  await page.waitForTimeout(200);

  // 全体を1拍／1小節ずらす
  await page.tap('#lyricClear');
  await page.waitForTimeout(300);
  await page.fill('#lyricInput', 'M9 ダミーX\nM10.2 ダミーY');
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  await page.tap('#shiftB1');
  await page.waitForTimeout(300);
  rec('全体を1拍うしろへずらせる',
      (await page.evaluate(() => JSON.stringify(window.__poc.lyrics)))
        === '{"8.1":"ダミーX","9.2":"ダミーY"}',
      await page.evaluate(() => JSON.stringify(window.__poc.lyrics)));
  await page.tap('#shiftB-1');
  await page.waitForTimeout(300);
  await page.tap('#shiftM1');
  await page.waitForTimeout(300);
  rec('全体を1小節うしろへずらせる',
      (await page.evaluate(() => JSON.stringify(window.__poc.lyrics)))
        === '{"9.0":"ダミーX","10.1":"ダミーY"}',
      await page.evaluate(() => JSON.stringify(window.__poc.lyrics)));
  await page.tap('#shiftM-1');
  await page.waitForTimeout(300);

  // 曲の外へは出さない
  await page.tap('#lyricClear');
  await page.waitForTimeout(200);
  await page.fill('#lyricInput', 'M1 ダミー先頭');
  await page.tap('#lyricApply');
  await page.waitForTimeout(300);
  await page.tap('#shiftB-1');
  await page.waitForTimeout(300);
  rec('曲の外へはずらさない',
      (await page.evaluate(() => window.__poc.lyrics['0.0'])) === 'ダミー先頭'
      && (await page.textContent('#lyricStat')).indexOf('ずらせませんでした') >= 0);

  // --- レビュー指摘1〜5の再発防止 ---

  // 指摘1: 歌詞に " が入っても属性を突破できず、本文も欠けない
  await page.tap('#lyricClear');
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    window.__pwned = 0;
    window.__poc.lyrics['0.0'] = 'a" autofocus onfocus="window.__pwned=1" x="';
    window.__poc.openLyricSheet(0);
  });
  await page.waitForTimeout(300);
  const attrs = await page.evaluate(() => {
    var el = document.querySelector('.lfield[data-b="0"]'), out = [], i;
    for(i = 0; i < el.attributes.length; i++){ out.push(el.attributes[i].name); }
    return { attrs: out, value: el.value };
  });
  rec('歌詞の " で属性を突破できない',
      attrs.attrs.indexOf('onfocus') < 0 && attrs.attrs.indexOf('autofocus') < 0,
      JSON.stringify(attrs.attrs));
  rec('" を含む歌詞が欠けずに編集欄へ入る',
      attrs.value === 'a" autofocus onfocus="window.__pwned=1" x="', attrs.value);
  await page.tap('#lyricSaveOne');
  await page.waitForTimeout(300);
  rec('" を含む歌詞が保存で切り捨てられない',
      (await page.evaluate(() => window.__poc.lyricAt(0, 0)))
        === 'a" autofocus onfocus="window.__pwned=1" x="',
      await page.evaluate(() => window.__poc.lyricAt(0, 0)));
  rec('スクリプトが実行されていない',
      (await page.evaluate(() => window.__pwned)) === 0);

  // 指摘2: 2/4小節へ寄せるときに断片が重なって消えない
  const twoFour = await page.evaluate(() => {
    var i, mb = window.__poc.measBeats;
    for(i = 0; i < mb.length; i++){ if(mb[i] !== 4){ return i; } }
    return -1;
  });
  rec('2/4小節の位置を特定できる', twoFour >= 0, 'index=' + twoFour);
  const collide = await page.evaluate(idx => {
    var L = window.__poc.lyrics, k;
    for(k in L){ if(L.hasOwnProperty(k)){ delete L[k]; } }
    L[(idx + 1) + '.1'] = 'A'; L[(idx + 1) + '.2'] = 'B'; L[(idx + 1) + '.3'] = 'C';
    var ok = window.__poc.shiftAllMeasures(-1);
    return { ok: ok, after: JSON.stringify(L) };
  }, twoFour);
  rec('2/4小節への重なりで断片を消さない',
      collide.ok === false
      && collide.after === '{"' + (twoFour + 1) + '.1":"A","' + (twoFour + 1)
         + '.2":"B","' + (twoFour + 1) + '.3":"C"}',
      JSON.stringify(collide));

  // 指摘3: 同じコードが続く小節でも、拍が進むと強調が移る
  await page.evaluate(() => {
    var L = window.__poc.lyrics, k;
    for(k in L){ if(L.hasOwnProperty(k)){ delete L[k]; } }
    L['0.0'] = 'ダミー前'; L['0.2'] = 'ダミー後';
    window.__poc.repaintAll();
  });
  await page.fill('#bpm', '200');
  await page.dispatchEvent('#bpm', 'change');
  await page.waitForTimeout(200);
  await page.tap('#reset');
  await page.waitForTimeout(200);
  const onAt0 = await page.textContent('.lyFrag.on');
  await page.tap('#play');
  await page.waitForTimeout(800);
  const onLater = await page.textContent('.lyFrag.on');
  await page.tap('#play');
  await page.tap('#reset');
  await page.waitForTimeout(200);
  rec('拍が進むと強調が次の断片へ移る',
      onAt0.trim() === 'ダミー前' && onLater.trim() === 'ダミー後',
      onAt0.trim() + ' -> ' + onLater.trim());
  await page.fill('#bpm', '85');
  await page.dispatchEvent('#bpm', 'change');
  await page.waitForTimeout(200);

  // 指摘4: 動かせなかったとき、画面と保存内容がずれない
  await page.evaluate(() => {
    var L = window.__poc.lyrics, k;
    for(k in L){ if(L.hasOwnProperty(k)){ delete L[k]; } }
    L['10.0'] = 'ダミー1'; L['10.1'] = 'ダミー2';
    window.__poc.store.set('aliens.lyrics.v1', JSON.stringify(L));
    window.__poc.openLyricSheet(10);
  });
  await page.waitForTimeout(300);
  await page.fill('.lfield[data-b="3"]', 'ダミー幽霊');
  await page.tap('.lnudge[data-b="0"][data-d="1"]');
  await page.waitForTimeout(400);
  const sync = await page.evaluate(() => ({
    mem: JSON.stringify(window.__poc.lyrics),
    stored: localStorage.getItem('aliens.lyrics.v1')
  }));
  rec('動かせなくてもメモリと保存内容が一致する', sync.mem === sync.stored,
      'mem=' + sync.mem + ' stored=' + sync.stored);
  await page.evaluate(() => window.__poc.closeSheet());
  await page.waitForTimeout(200);

  // 指摘5: 移動してもページのスクロール位置が失われない
  await page.evaluate(() => {
    var L = window.__poc.lyrics, k;
    for(k in L){ if(L.hasOwnProperty(k)){ delete L[k]; } }
    L['40.0'] = 'ダミー移動';
    window.__poc.repaintAll();
    window.scrollTo(0, 1500);
  });
  await page.waitForTimeout(300);
  const beforeScroll = await page.evaluate(() => window.pageYOffset);
  await page.evaluate(() => window.__poc.openLyricSheet(40));
  await page.waitForTimeout(300);
  await page.tap('.lnudge[data-b="0"][data-d="1"]');
  await page.waitForTimeout(400);
  await page.evaluate(() => window.__poc.closeSheet());
  await page.waitForTimeout(300);
  const afterScroll = await page.evaluate(() => window.pageYOffset);
  rec('移動してもスクロール位置が戻る', Math.abs(afterScroll - beforeScroll) < 5,
      beforeScroll + ' -> ' + afterScroll);

  await page.tap('#lyricClear');
  await page.waitForTimeout(300);
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
