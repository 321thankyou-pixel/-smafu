# -*- coding: utf-8 -*-
"""WebKitGTK (Safari と同じ WebKit エンジン) で受入テストを自動実行する。
実HTTPサーバ経由で読み込むので localStorage の再読み込み保持も検証できる。"""
import sys, time, json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.webkitgtk.options import Options

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/index.html'
results = []
def rec(name, ok, detail=''):
    results.append((name, ok, detail))
    print(('PASS ' if ok else 'FAIL ') + name + ('  ' + detail if detail else ''))

opts = Options()
opts.set_capability('browserName', 'MiniBrowser')
opts.set_capability('webkitgtk:browserOptions', {'args': ['--automation']})
d = webdriver.WebKitGTK(options=opts)
try:
    d.set_window_size(390, 844)
    d.get(URL)
    time.sleep(1.5)

    ua = d.execute_script('return navigator.userAgent')
    rec('エンジン確認 (WebKit)', 'AppleWebKit' in ua and 'Chrome' not in ua, ua[:90])

    errbox = d.execute_script("return document.getElementById('errbox').style.display")
    rec('JSエラーなし', errbox != 'block',
        d.execute_script("return document.getElementById('errbox').textContent"))

    rec('① JS動作バッジ OK',
        d.find_element(By.ID, 'b1').text == 'OK')
    rec('② localStorage 利用可',
        d.find_element(By.ID, 'b2').text == 'OK')

    # 出発点: ピンクの「次」カード（v9でタップできなかったコード）
    nextcard = d.find_element(By.CSS_SELECTOR, '.card.next')
    chord = nextcard.get_attribute('data-chord')
    before_form = nextcard.find_element(By.CSS_SELECTOR, '.form').text
    before_dots = d.execute_script(
        "return Array.prototype.map.call("
        "document.querySelector('.card.next').querySelectorAll('.dot'),"
        "function(e){return e.style.left;}).join(',')")
    rec('次コードにフォームが登録されている (%s)' % chord,
        before_form not in ('', 'フォーム未登録'), before_form)
    rec('ダイアグラムのドットが描画されている', len(before_dots) > 0, before_dots)

    nextcard.click()
    time.sleep(0.6)
    rec('③ タップでボトムシートが開く',
        'open' in d.find_element(By.ID, 'sheet').get_attribute('class'))
    opts_el = d.find_elements(By.CSS_SELECTOR, '#voiceOptions .vopt')
    rec('③ フォーム候補が複数表示される', len(opts_el) >= 2, '%d件' % len(opts_el))
    rec('③ バッジ b3 = OK', d.find_element(By.ID, 'b3').text == 'OK')

    # 2番目の候補を選択
    target_form = opts_el[1].find_element(By.CSS_SELECTOR, '.vform').text
    opts_el[1].click()
    time.sleep(0.6)
    after_form = d.execute_script(
        "return document.querySelector('.card.next .form').textContent")
    after_dots = d.execute_script(
        "return Array.prototype.map.call("
        "document.querySelector('.card.next').querySelectorAll('.dot'),"
        "function(e){return e.style.left;}).join(',')")
    rec('④ 選択でカードのフォーム表記が即時変化',
        after_form == target_form and after_form != before_form,
        '%s -> %s' % (before_form, after_form))
    rec('④ ダイアグラムの押弦位置も変化', after_dots != before_dots,
        '%s -> %s' % (before_dots, after_dots))
    rec('④ バッジ b4 = OK', d.find_element(By.ID, 'b4').text == 'OK')

    saved = d.execute_script(
        "return localStorage.getItem('aliens.voicing.' + arguments[0])", chord)
    rec('選択が localStorage に保存された', saved == '1', 'value=%r' % saved)

    d.find_element(By.ID, 'closeSheet').click()
    time.sleep(0.4)
    rec('シートが閉じる', 'open' not in d.find_element(By.ID, 'sheet').get_attribute('class'))

    # --- リロード ---
    d.refresh()
    time.sleep(1.5)
    reloaded_form = d.execute_script(
        "return document.querySelector('.card.next .form').textContent")
    rec('⑤ 再読み込み後も選択フォームが保持される',
        reloaded_form == target_form, '%s (期待 %s)' % (reloaded_form, target_form))
    rec('⑤ バッジ b5 = OK', d.find_element(By.ID, 'b5').text == 'OK',
        d.find_element(By.ID, 't5').text[:80])

    # スクリムで閉じられるか (iOS Safari の div タップ問題対策の確認)
    d.find_element(By.CSS_SELECTOR, '.card.current').click()
    time.sleep(0.5)
    from selenium.webdriver.common.action_chains import ActionChains
    scrim = d.find_element(By.ID, 'scrim')
    ActionChains(d).move_to_element_with_offset(scrim, 0, -380).click().perform()
    time.sleep(0.5)
    rec('背景タップでシートが閉じる',
        'open' not in d.find_element(By.ID, 'sheet').get_attribute('class'))

    # 全コードのフォーム表記がパースできるか
    bad = d.execute_script("""
      var v = window.__poc.voicings, bad = [];
      for (var c in v) { for (var i=0;i<v[c].length;i++) {
        var h = window.__poc.diagram(v[c][i].form);
        if (h.indexOf('フォーム表記エラー') >= 0) bad.push(c + ':' + v[c][i].form);
      } }
      return bad;""")
    rec('全フォームがダイアグラム化できる', len(bad) == 0, str(bad))

    # 未登録コードが無いか
    miss = d.execute_script("""
      var ms = %s; var v = window.__poc.voicings; var miss = [];
      for (var i=0;i<ms.length;i++){ for(var j=0;j<ms[i].chords.length;j++){
        var c = ms[i].chords[j][0];
        if (c !== 'N.C.' && !v[c] && miss.indexOf(c)<0) miss.push(c); } }
      return miss;""" % 'window.__poc && []' if False else """
      var v = window.__poc.voicings, miss = [];
      var els = document.querySelectorAll('.mc');
      for (var i=0;i<els.length;i++){
        var c = els[i].childNodes[0].nodeValue;
        if (c && c !== 'N.C.' && !v[c] && miss.indexOf(c) < 0) miss.push(c);
      }
      return miss;""")
    rec('譜面上の全コードにフォーム候補がある', len(miss) == 0, str(miss))

    d.get_screenshot_as_file('/home/user/work/webkit_shot.png')
finally:
    d.quit()

ng = [r for r in results if not r[1]]
print('\n===== WebKit 結果: %d/%d PASS =====' % (len(results) - len(ng), len(results)))
sys.exit(1 if ng else 0)
