# -*- coding: utf-8 -*-
"""iPhone Safari 実機検証用 PoC（v12）を1枚のHTMLとして生成する。"""
import json, io, os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# 小節・構成データは v11 (aliens_nav_v11_browser_verified.html) から取り出したものを
# tools/measures.json として同梱している。内容は改変していない。
measures = json.load(io.open(os.path.join(HERE, 'measures.json'), encoding='utf-8'))
voicings = json.load(io.open(os.path.join(HERE, 'voicings.json'), encoding='utf-8'))

OPEN = [4, 9, 2, 7, 11, 4]
NAME = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def notes_of(frets):
    out = []
    for i, v in enumerate(frets):
        if v == 'x':
            continue
        out.append(NAME[(OPEN[i] + v) % 12])
    out.reverse()   # 1弦->6弦 の表示順ではなく低音->高音のままにするので戻す
    out.reverse()
    return out

# 表示用に音名を付与
for chord, opts in voicings.items():
    for o in opts:
        o['notes'] = ' '.join(notes_of(o['frets']))
        del o['frets']

used = []
for mm in measures:
    for c in mm['chords']:
        if c[0] not in used:
            used.append(c[0])
missing = [c for c in used if c not in voicings and c != 'N.C.']

def diagram_html(form):
    """静的HTML用。JS側と同じ描画規則。"""
    parts = form.split('-') if '-' in form else list(form)
    vals = ['x' if p.lower() == 'x' else int(p) for p in parts]
    rows = list(reversed(vals))            # 1弦を上に
    fretted = [v for v in vals if isinstance(v, int) and v > 0]
    has_open = any(v == 0 for v in vals)
    if not fretted:
        start = 1
    elif has_open and max(fretted) <= 5:
        start = 1                       # 開放弦を含むローコードはナットから描く
    else:
        start = min(fretted)
        if max(fretted) - start > 4:
            start = max(1, max(fretted) - 4)
    if fretted and (min(fretted) < start or max(fretted) > start + 4):
        return '<div class="noDiagram">フォーム表記エラー</div>'
    out = []
    for i, v in enumerate(rows):
        mark = '&times;' if v == 'x' else ('&#9675;' if v == 0 else '')
        dot = ''
        if isinstance(v, int) and v > 0:
            pct = ((v - start + .5) / 5) * 100
            dot = '<span class="dot" style="left:%.2f%%"></span>' % pct
        out.append('<div class="sRow"><div class="sLab">%d %s</div>'
                   '<div class="sLine"><div class="fg"><i></i><i></i><i></i><i></i><i></i></div>%s</div></div>'
                   % (i + 1, mark, dot))
    out.append('<div class="fretNo">%dF〜</div>' % (start if fretted else 1))
    cls = 'dg nut' if (not fretted or start == 1) else 'dg'
    return '<div class="%s">%s</div>' % (cls, ''.join(out))

# ---- 静的譜面 ----
score = []
prev_section = None
for mi, mm in enumerate(measures):
    if mm['section'] != prev_section:
        score.append('<div class="sec">%s</div>' % mm['section'])
        prev_section = mm['section']
    total = sum(c[1] for c in mm['chords']) or 1
    cells = ''.join(
        '<div class="mc" style="width:%.4f%%">%s<small>%d拍</small></div>' % (c[1] * 100.0 / total, c[0], c[1])
        for c in mm['chords'])
    cue = ('<span class="cue">%s</span>' % mm['cue']) if mm['cue'] else ''
    # 歌詞は端末内にのみ保存するため、生成物には一切埋め込まない
    score.append('<button class="mini" type="button" data-mi="%d">'
                 '<span class="mtop"><span class="mno">M%d</span>%s</span>'
                 '<span class="mchords">%s</span>'
                 '<span class="mlyric" data-mlyric="%d"></span></button>'
                 % (mi, mi + 1, cue, cells, mi))
score_html = ''.join(score)

# 初期表示（静的）
seq = []
for mi, mm in enumerate(measures):
    for ci, c in enumerate(mm['chords']):
        seq.append({'mi': mi, 'chord': c[0], 'beats': c[1]})

def card_static(role, cls, item):
    ch = item['chord']
    opts = voicings.get(ch)
    if opts:
        f = opts[0]['form']
        body = '<div class="form">%s</div><div class="diagram">%s</div>' % (f, diagram_html(f))
    else:
        body = '<div class="form">フォーム未登録</div><div class="diagram"><div class="noDiagram">—</div></div>'
    n = len(ch)
    ccls = 'chord' if n <= 4 else ('chord len1' if n <= 6 else ('chord len2' if n <= 9 else 'chord len3'))
    return ('<button class="card %s" type="button" data-slot="%s"><div class="role">%s</div>'
            '<div class="%s">%s</div>%s<div class="tapmark">タップで変更</div></button>'
            % (cls, cls, role, ccls, ch, body))

cards_html = (card_static('現在', 'current', seq[0])
              + card_static('次', 'next', seq[1])
              + card_static('その次', 'after', seq[2]))

TPL = u'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="format-detection" content="telephone=no">
<title>エイリアンズ コードフォーム選択 PoC v12</title>
<style>
:root{--pink:#ff2f92;--ink:#111;--line:#e5e5e5;--ok:#0a8f3c;--ng:#c0261c}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:#efefed;color:#111;-webkit-text-size-adjust:100%;
 font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Yu Gothic",Meiryo,sans-serif}
button{font:inherit;color:inherit;-webkit-appearance:none;appearance:none;
 -webkit-tap-highlight-color:rgba(255,47,146,.18);touch-action:manipulation;cursor:pointer}
.app{max-width:430px;margin:0 auto;background:#fff;min-height:100vh}
header{position:-webkit-sticky;position:sticky;top:0;z-index:30;background:#fff;padding:11px 12px;border-bottom:1px solid #eee}
h1{font-size:19px;margin:0}
.meta{font-size:10px;color:#777;margin-top:3px}
main{padding:10px 10px 92px}

/* 受入テストパネル */
.panel{border:2px solid #111;border-radius:14px;padding:10px;margin-bottom:12px;background:#fcfcfc}
.panel h2{font-size:12px;margin:0 0 7px}
.chk{display:flex;gap:7px;align-items:flex-start;font-size:11px;line-height:1.45;margin:4px 0}
.badge{flex:none;min-width:34px;text-align:center;font-size:10px;font-weight:900;border-radius:999px;padding:2px 5px;background:#eee;color:#555}
.badge.ok{background:var(--ok);color:#fff}
.badge.ng{background:var(--ng);color:#fff}
.badge.wait{background:#e6a100;color:#fff}
.panel .hint{font-size:10px;color:#777;margin-top:7px;line-height:1.5}
#errbox{display:none;background:#fdecea;border:1px solid var(--ng);color:var(--ng);
 border-radius:10px;padding:9px;font-size:11px;margin-bottom:10px;white-space:pre-wrap;word-break:break-all}

.sectionTitle{font-size:10px;font-weight:900;color:#777;margin:12px 0 5px}
.lyric{font-size:20px;font-weight:900;text-align:center;padding:10px;border:1px solid #ddd;border-radius:14px}
.lyric small{display:block;font-size:10px;color:#999;margin-top:5px;font-weight:400}
.nav{display:grid;grid-template-columns:.95fr 1.55fr .9fr;gap:8px;align-items:start;margin-top:12px}
.card{width:100%;border:1px solid #ddd;border-radius:15px;padding:9px 6px;text-align:center;background:#fff;min-width:0;display:block}
.card.current{border:2px solid #111;background:#fafafa}
.card.next{border:2px solid var(--pink);box-shadow:0 5px 16px rgba(255,47,146,.14)}
.card.after{opacity:.62}
.card:active{background:#f1f1f1}
.role{font-size:9px;font-weight:900;color:#888}
.next .role{color:var(--pink)}
.chord{font-weight:900;line-height:1.1;word-break:keep-all;overflow-wrap:break-word}
.card .chord{font-size:21px}
.next .chord{font-size:29px}
/* 長い名前（Baug7(#9) / F#(b9)/Bb など）は切らずに縮める */
.card .chord.len2{font-size:17px}
.card .chord.len3{font-size:14px}
.next .chord.len1{font-size:25px}
.next .chord.len2{font-size:21px}
.next .chord.len3{font-size:17px}
.form{font-size:9px;color:#777;margin-top:2px;min-height:12px;word-break:break-all}
.diagram{margin-top:6px}
.tapmark{font-size:8px;color:var(--pink);font-weight:900;margin-top:5px}
.sRow{display:grid;grid-template-columns:17px 1fr;align-items:center;height:13px}
.sLab{font-size:7px;color:#666}
.sLine{position:relative;border-top:1px solid #333;height:100%}
.fg{position:absolute;left:0;right:0;top:0;bottom:0;
 display:-webkit-box;display:-webkit-flex;display:flex}
.fg i{-webkit-box-flex:1;-webkit-flex:1 1 20%;flex:1 1 20%;border-left:1px solid #666}
.nut .fg i:first-child{border-left:3px solid #111}
.fg i:last-child{border-right:1px solid #666}
.dot{position:absolute;width:9px;height:9px;top:-4px;background:#111;border-radius:50%;
 -webkit-transform:translateX(-50%);transform:translateX(-50%)}
.noDiagram{font-size:8px;color:#aaa;padding:10px 0}
.fretNo{font-size:7px;color:#999;text-align:right;padding-right:2px;margin-top:1px}

.bar{height:6px;background:#eee;border-radius:999px;overflow:hidden;margin-top:12px}
.bar i{display:block;height:100%;width:0;background:var(--pink)}
.controls{display:flex;gap:7px;margin-top:10px}
.ctrl{border:0;border-radius:10px;padding:9px 12px;font-weight:900;background:#111;color:#fff}
.ctrl.alt{background:#eee;color:#111}

.look{margin-top:18px;border-top:1px solid #eee;padding-top:10px}
.lookhead{font-size:12px;font-weight:900;margin-bottom:8px}
.sec{font-size:10px;font-weight:900;color:#666;margin:12px 2px 5px;display:flex;align-items:center;gap:7px}
.sec:before,.sec:after{content:"";height:1px;background:#ddd;flex:1}
.mini{display:block;width:100%;text-align:left;font:inherit;color:inherit;
 border:1px solid #e0e0e0;border-radius:10px;padding:6px 7px;margin:0 0 6px;background:#fafafa}
.mini:active{background:#f0f0f0}
.mini.activeMeasure{border:2px solid #111;background:#fff}
.mtop{display:flex;justify-content:space-between;align-items:center;gap:6px}
.mno{font-size:9px;font-weight:900;color:#888}
.cue{font-size:8px;font-weight:900;background:#111;color:#fff;border-radius:999px;padding:2px 6px}
.mchords{display:flex;margin-top:5px;border:1px solid #ddd;border-radius:6px;overflow:hidden;background:#fff}
.mc{text-align:center;padding:4px 2px;border-right:1px solid #ddd;font-size:11px;font-weight:900;min-width:0;overflow:hidden}
.mc:last-child{border-right:0}
.mc small{display:block;font-size:7px;color:#999;font-weight:400}

/* ボトムシート */
.scrim{position:fixed;left:0;right:0;top:0;bottom:0;background:rgba(0,0,0,.4);z-index:50;display:none;
 border:0;width:100%;padding:0;margin:0}
.scrim.open{display:block}
.sheet{position:fixed;left:0;right:0;bottom:0;z-index:51;background:#fff;
 border-radius:18px 18px 0 0;max-height:80%;overflow-y:auto;-webkit-overflow-scrolling:touch;
 padding:13px 12px 18px;padding-bottom:calc(18px + env(safe-area-inset-bottom));display:none;
 max-width:430px;margin:0 auto}
.sheet.open{display:block}
.sheetHead{display:flex;align-items:center;justify-content:space-between;gap:10px}
.sheetTitle{font-size:18px;font-weight:900}
.closeBtn{border:0;background:#eee;border-radius:999px;width:36px;height:36px;font-size:18px;font-weight:900}
.sheetNote{font-size:10px;color:#888;margin:5px 0 10px;line-height:1.5}
.vopt{width:100%;border:1px solid #ddd;border-radius:13px;background:#fff;padding:10px;margin:0 0 9px;
 text-align:left;display:grid;grid-template-columns:1fr 118px;gap:10px;align-items:center}
.vopt.selected{border:2px solid var(--pink);background:#fff6fa}
.vopt>span{display:block;min-width:0}
.vname{display:block;font-size:15px;font-weight:900}
.vform{display:block;font-size:12px;color:#444;margin-top:3px;word-break:break-all;
 font-family:ui-monospace,Menlo,monospace;letter-spacing:.04em}
.vnotes{display:block;font-size:10px;color:#888;margin-top:3px}
.vsrc{display:block;font-size:9px;color:#999;margin-top:3px}
.vsel{display:block;font-size:10px;color:var(--pink);font-weight:900;margin-top:5px}
/* 歌詞（端末内保存） */
.lyricPanel{border:1px solid #ddd;border-radius:14px;padding:11px;margin-top:16px;background:#fcfcfc}
.lyricPanel h2{font-size:12px;margin:0 0 6px}
.lyricPanel p{font-size:10px;color:#777;line-height:1.65;margin:0 0 8px}
.lyricPanel textarea{display:block;width:100%;min-height:104px;padding:8px;border:1px solid #ccc;
 border-radius:10px;background:#fff;color:#111;resize:vertical;-webkit-appearance:none;appearance:none;
 font:12px/1.65 -apple-system,BlinkMacSystemFont,"Hiragino Sans","Yu Gothic",Meiryo,sans-serif}
.lyricRow{display:flex;gap:7px;align-items:center;margin-top:8px;flex-wrap:wrap}
.lyricRow label{font-size:10px;color:#666}
.lyricRow input{width:62px;padding:6px 7px;border:1px solid #ccc;border-radius:8px;background:#fff;color:#111;
 font:12px -apple-system,BlinkMacSystemFont,sans-serif;-webkit-appearance:none;appearance:none}
.lyricStat{font-size:10px;font-weight:900;margin-top:8px;color:#444}
.lyricStat b{color:var(--pink)}
.ctrl.sm{padding:7px 10px;font-size:12px}
.mlyric{font-size:10px;color:#555;line-height:1.5;margin-top:4px;font-weight:400;
 white-space:pre-wrap;word-break:break-word}
.lyricEditBox{display:block;width:100%;min-height:76px;padding:8px;border:1px solid #ccc;border-radius:10px;
 background:#fff;color:#111;-webkit-appearance:none;appearance:none;
 font:14px/1.6 -apple-system,BlinkMacSystemFont,"Hiragino Sans","Yu Gothic",Meiryo,sans-serif}
.bottom{position:fixed;left:0;right:0;bottom:0;z-index:25;background:#fff;border-top:1px solid #eee;
 padding:7px 12px;padding-bottom:calc(7px + env(safe-area-inset-bottom));max-width:430px;margin:0 auto}
.songbar{height:4px;background:#eee;border-radius:999px;overflow:hidden}
.songbar i{display:block;height:100%;width:0;background:var(--pink)}
.brow{display:flex;justify-content:space-between;font-size:10px;color:#666;margin-top:5px}
</style>
</head>
<body>
<div class="app">
<header>
 <h1>エイリアンズ</h1>
 <div class="meta">Play: G / 半音下げチューニング ・ 4/4 ・ BPM 85 ・ 126小節</div>
</header>
<main>

<div id="errbox"></div>

<div class="panel">
 <h2>iPhone Safari 受入テスト</h2>
 <div class="chk"><span class="badge" id="b1">…</span><span>① JavaScriptが動いている</span></div>
 <div class="chk"><span class="badge" id="b2">…</span><span>② 保存領域（localStorage）が使える</span></div>
 <div class="chk"><span class="badge" id="b3">…</span><span id="t3">③ コードカードをタップ → 候補が出る</span></div>
 <div class="chk"><span class="badge" id="b4">…</span><span id="t4">④ 候補を選ぶ → ダイアグラムが即時に変わる</span></div>
 <div class="chk"><span class="badge" id="b5">…</span><span id="t5">⑤ 再読み込み後も選択が残っている</span></div>
 <div class="hint" id="hint">③④を手で操作したあと、このページを<b>下に引いて再読み込み</b>してください。⑤が緑になれば受入テスト合格です。</div>
 <div class="controls">
  <button class="ctrl alt" id="btnReload" type="button">↻ 再読み込み</button>
  <button class="ctrl alt" id="btnClear" type="button">保存を消す</button>
 </div>
</div>

<div class="sectionTitle" id="sectionTitle">__SECTION__</div>
<div class="lyric" id="lyric">__LYRIC__<small>__METER__</small></div>

<div class="nav" id="nav">__CARDS__</div>
<div class="bar"><i id="codebar"></i></div>
<div class="controls">
 <button class="ctrl" id="play" type="button">▶ 再生</button>
 <button class="ctrl alt" id="reset" type="button">↺ 戻す</button>
</div>

<div class="lyricPanel">
 <h2>歌詞（この端末にだけ保存されます）</h2>
 <p>入力した歌詞は<b>あなたの端末の中だけ</b>に保存されます。どこにも送信されず、公開もされません。<br>
  書式は2通り。どちらでも読み取ります。<br>
  ・<b>小節番号つき</b>：<code>M9 歌詞</code> / <code>9: 歌詞</code> のように行頭に小節番号<br>
  ・<b>番号なし</b>：1行＝1小節。下の「開始小節」から順に割り当てます（空行はその小節を空にします）</p>
 <textarea id="lyricInput" placeholder="M9 …&#10;M10 …&#10;&#10;または1行＝1小節で貼り付け"></textarea>
 <div class="lyricRow">
  <label for="lyricStart">開始小節</label><input id="lyricStart" type="number" min="1" max="126" value="9">
  <button class="ctrl sm" id="lyricApply" type="button">取り込む</button>
  <button class="ctrl alt sm" id="lyricExport" type="button">書き出す</button>
  <button class="ctrl alt sm" id="lyricClear" type="button">歌詞を全部消す</button>
 </div>
 <div class="lyricStat" id="lyricStat">未登録</div>
 <p style="margin:8px 0 0">小節をタップすると、その小節の歌詞だけを直接なおせます。
  Safariは長期間使わないページの保存データを消すことがあるため、
  入力後は「書き出す」でテキストを控えておくことをおすすめします。</p>
</div>

<div class="look">
 <div class="lookhead">全曲譜面（先読み）</div>
 __SCORE__
 </div>
</main>

<div class="bottom">
 <div class="songbar"><i id="songbar"></i></div>
 <div class="brow"><span id="time">00:00</span><span id="stamp">v12 PoC</span></div>
</div>
</div>

<button class="scrim" id="scrim" type="button" aria-label="閉じる"></button>
<div class="sheet" id="sheet" role="dialog" aria-modal="true" aria-labelledby="sheetTitle">
 <div class="sheetHead"><div class="sheetTitle" id="sheetTitle">コードフォーム</div>
  <button class="closeBtn" id="closeSheet" type="button" aria-label="閉じる">&times;</button></div>
 <div class="sheetNote" id="sheetNote">表示するフォームを選びます。選択は同じコード名の全出現箇所に適用され、この端末に保存されます。<br>
  掲載フォームは構成音を機械検証済み（押弦4本以内・4フレット幅以内）。</div>
 <div id="voiceOptions"></div>
</div>

<script>
window.onerror = function(msg, url, line, col){
  try{
    var b = document.getElementById('errbox');
    b.style.display = 'block';
    b.textContent = 'JSエラー: ' + msg + ' (行' + line + ':' + col + ')';
    var e1 = document.getElementById('b1');
    e1.className = 'badge ng'; e1.textContent = 'NG';
  }catch(e){}
  return false;
};
(function(){
"use strict";
var measures = __MEASURES__;
var voicings = __VOICINGS__;
var STORE_PREFIX = 'aliens.voicing.';
var STAMP_KEY = 'aliens.savedAt';

/* ---------- 保存 ---------- */
var store = (function(){
  var mem = {}, usable = false;
  try{
    localStorage.setItem('__t__','1');
    usable = (localStorage.getItem('__t__') === '1');
    localStorage.removeItem('__t__');
  }catch(e){ usable = false; }
  return {
    usable: function(){ return usable; },
    get: function(k){
      try{ return usable ? localStorage.getItem(k) : (mem.hasOwnProperty(k) ? mem[k] : null); }
      catch(e){ return mem.hasOwnProperty(k) ? mem[k] : null; }
    },
    set: function(k,v){
      v = String(v); mem[k] = v;
      if(usable){ try{ localStorage.setItem(k,v); }catch(e){} }
    },
    remove: function(k){
      delete mem[k];
      if(usable){ try{ localStorage.removeItem(k); }catch(e){} }
    },
    keys: function(){
      var out = [], i, k;
      if(usable){
        try{
          for(i=0;i<localStorage.length;i++){
            k = localStorage.key(i);
            if(k && k.indexOf(STORE_PREFIX) === 0){ out.push(k); }
          }
          return out;
        }catch(e){}
      }
      for(k in mem){ if(mem.hasOwnProperty(k) && k.indexOf(STORE_PREFIX) === 0){ out.push(k); } }
      return out;
    },
    clearAll: function(){
      var ks = this.keys(), i;
      for(i=0;i<ks.length;i++){
        delete mem[ks[i]];
        if(usable){ try{ localStorage.removeItem(ks[i]); }catch(e){} }
      }
      delete mem[STAMP_KEY];
      if(usable){ try{ localStorage.removeItem(STAMP_KEY); }catch(e){} }
    }
  };
})();

/* ---------- 選択状態 ---------- */
var selected = {};
var restored = [];
(function(){
  var ks = store.keys(), i, chord, raw, n;
  for(i=0;i<ks.length;i++){
    chord = ks[i].substring(STORE_PREFIX.length);
    if(!voicings.hasOwnProperty(chord)) { continue; }
    raw = store.get(ks[i]);
    n = parseInt(raw, 10);
    if(isNaN(n) || n < 0 || n >= voicings[chord].length){
      store.remove(ks[i]);   /* 壊れた保存値は残さない */
      continue;
    }
    selected[chord] = n;
    restored.push(chord + ' → ' + voicings[chord][n].form);
  }
})();
function sel(chord){ return selected.hasOwnProperty(chord) ? selected[chord] : 0; }

/* ---------- 歌詞（端末内にのみ保存。ネットワークへは一切送らない） ---------- */
var LYRIC_KEY = 'aliens.lyrics.v1';
var lyrics = {};
(function(){
  var raw = store.get(LYRIC_KEY), obj = null, k;
  if(!raw){ return; }
  try { obj = JSON.parse(raw); } catch(e) { obj = null; }
  if(!obj || typeof obj !== 'object'){ return; }
  for(k in obj){
    if(obj.hasOwnProperty(k) && typeof obj[k] === 'string' && obj[k] !== ''){
      lyrics[k] = obj[k];
    }
  }
})();
function lyricOf(mi){
  var k = String(mi);
  return lyrics.hasOwnProperty(k) ? lyrics[k] : '';
}
function lyricCount(){
  var n = 0, k;
  for(k in lyrics){ if(lyrics.hasOwnProperty(k) && lyrics[k]){ n++; } }
  return n;
}
function saveLyrics(){
  store.set(LYRIC_KEY, JSON.stringify(lyrics));
  store.set(STAMP_KEY, new Date().toISOString());
}
function esc(t){
  return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function matchNumbered(line){
  var m = line.match(/^[Mm]\s*(\d{1,3})\s*[:\\uff1a]?\s*(.*)$/);
  if(!m){ m = line.match(/^(\d{1,3})\s*[:\\uff1a]\s*(.*)$/); }
  if(!m){ m = line.match(/^(\d{1,3})[ \\t\\u3000]+(.*)$/); }
  if(!m){ return null; }
  return { no: parseInt(m[1], 10), text: m[2] };
}
function parseLyricText(text, startNo){
  var raw = String(text).split('\\n'), lines = [], i, ln, hit = 0, nonEmpty = 0,
      out = {}, mi, mm;
  for(i = 0; i < raw.length; i++){
    ln = raw[i];
    if(ln.charAt(ln.length - 1) === '\\r'){ ln = ln.slice(0, -1); }
    lines.push(ln);
    if(ln.replace(/^\s+|\s+$/g, '') !== ''){
      nonEmpty++;
      if(matchNumbered(ln)){ hit++; }
    }
  }
  if(nonEmpty === 0){ return { mode: 'empty', map: {}, count: 0 }; }
  if(hit >= Math.ceil(nonEmpty * 0.6)){
    for(i = 0; i < lines.length; i++){
      mm = matchNumbered(lines[i]);
      if(!mm){ continue; }
      mi = mm.no - 1;
      if(mi < 0 || mi >= measures.length){ continue; }
      if(mm.text !== ''){ out[String(mi)] = mm.text; }
    }
    return { mode: 'numbered', map: out, count: countKeys(out) };
  }
  mi = startNo - 1;
  for(i = 0; i < lines.length; i++){
    if(mi >= measures.length){ break; }
    ln = lines[i].replace(/^\s+|\s+$/g, '');
    if(ln !== ''){ out[String(mi)] = ln; }
    mi++;
  }
  return { mode: 'sequential', map: out, count: countKeys(out) };
}
function countKeys(o){ var n = 0, k; for(k in o){ if(o.hasOwnProperty(k)){ n++; } } return n; }
function exportLyricText(){
  var i, k, out = [];
  for(i = 0; i < measures.length; i++){
    k = String(i);
    if(lyrics.hasOwnProperty(k) && lyrics[k]){ out.push('M' + (i + 1) + ' ' + lyrics[k]); }
  }
  return out.join('\\n');
}

/* ---------- ダイアグラム ---------- */
function parseForm(form){
  var parts = (form.indexOf('-') >= 0) ? form.split('-') : form.split('');
  var out = [], i, p, n;
  if(parts.length !== 6){ return null; }
  for(i=0;i<6;i++){
    p = parts[i];
    if(p === 'x' || p === 'X'){ out.push('x'); continue; }
    n = parseInt(p, 10);
    if(isNaN(n) || n < 0 || n > 24){ return null; }
    out.push(n);
  }
  return out;
}
function diagram(form){
  var vals = parseForm(form), i, v, rows, fretted = [], hasOpen = false,
      start, html = '', pct, mark, dot, lo, hi;
  if(!vals){ return '<div class="noDiagram">フォーム表記エラー</div>'; }
  for(i=0;i<6;i++){
    if(vals[i] === 'x'){ continue; }
    if(vals[i] === 0){ hasOpen = true; } else { fretted.push(vals[i]); }
  }
  if(!fretted.length){
    start = 1;
  } else {
    lo = Math.min.apply(null, fretted); hi = Math.max.apply(null, fretted);
    if(hasOpen && hi <= 5){
      start = 1;                    /* 開放弦を含むローコードはナットから描く */
    } else {
      start = lo;
      if(hi - start > 4){ start = Math.max(1, hi - 4); }
    }
    if(lo < start || hi > start + 4){
      return '<div class="noDiagram">フォーム表記エラー</div>';
    }
  }
  rows = vals.slice(0).reverse();   /* 1弦を上に */
  for(i=0;i<6;i++){
    v = rows[i]; mark = ''; dot = '';
    if(v === 'x'){ mark = '\\u00d7'; }
    else if(v === 0){ mark = '\\u25cb'; }
    else {
      pct = ((v - start + 0.5) / 5) * 100;
      dot = '<span class="dot" style="left:' + pct.toFixed(2) + '%"></span>';
    }
    html += '<div class="sRow"><div class="sLab">' + (i+1) + ' ' + mark + '</div>'
          + '<div class="sLine"><div class="fg"><i></i><i></i><i></i><i></i><i></i></div>'
          + dot + '</div></div>';
  }
  html += '<div class="fretNo">' + (fretted.length ? start : 1) + 'F\\u301c</div>';
  return '<div class="' + ((!fretted.length || start === 1) ? 'dg nut' : 'dg') + '">' + html + '</div>';
}

/* ---------- 進行データ ---------- */
var seq = [], mi, ci, mm;
for(mi=0;mi<measures.length;mi++){
  mm = measures[mi];
  for(ci=0;ci<mm.chords.length;ci++){
    seq.push({mi:mi, chord:mm.chords[ci][0], beats:mm.chords[ci][1]});
  }
}
var BPM = 85, BEATMS = 60000 / BPM;
var totalBeats = 0;
for(mi=0;mi<seq.length;mi++){ totalBeats += seq[mi].beats; }
var duration = totalBeats * BEATMS;

/* ---------- カード ---------- */
var cards = {
  current: document.querySelector('.card.current'),
  next: document.querySelector('.card.next'),
  after: document.querySelector('.card.after')
};
function chordSizeClass(chord){
  var n = chord.length;
  if(n <= 4){ return 'chord'; }
  if(n <= 6){ return 'chord len1'; }
  if(n <= 9){ return 'chord len2'; }
  return 'chord len3';
}
function renderCard(el, chord){
  var opts = voicings[chord], v, ce;
  el.setAttribute('data-chord', chord);
  ce = el.querySelector('.chord');
  ce.className = chordSizeClass(chord);
  ce.textContent = chord;
  if(opts && opts.length){
    v = opts[sel(chord)];
    el.querySelector('.form').textContent = v.form;
    el.querySelector('.diagram').innerHTML = diagram(v.form);
    el.querySelector('.tapmark').textContent = 'タップで変更（' + opts.length + '種）';
  } else {
    el.querySelector('.form').textContent = 'フォーム未登録';
    el.querySelector('.diagram').innerHTML = '<div class="noDiagram">\\u2014</div>';
    el.querySelector('.tapmark').textContent = '候補なし';
  }
}

function paintScoreLyrics(){
  var els = document.querySelectorAll('[data-mlyric]'), i, mi, t;
  for(i = 0; i < els.length; i++){
    mi = parseInt(els[i].getAttribute('data-mlyric'), 10);
    t = lyricOf(mi);
    els[i].innerHTML = t ? esc(t) : '';
  }
}
function paintLyricStat(){
  var n = lyricCount(), el = document.getElementById('lyricStat');
  el.innerHTML = n ? ('登録済み <b>' + n + '</b> 小節（この端末のみ）') : '未登録';
}

/* ---------- ボトムシート ---------- */
var sheetChord = null, sheetMi = -1, sheetMode = 'voicing', scrollY = 0;
var scrim = document.getElementById('scrim');
var sheet = document.getElementById('sheet');
var voiceBox = document.getElementById('voiceOptions');

function paintOptions(chord){
  var opts = voicings[chord], i, v, cur = sel(chord), html = '';
  if(!opts || !opts.length){
    voiceBox.innerHTML = '<div class="sheetNote">このコードにはフォーム候補が登録されていません。</div>';
    return;
  }
  for(i=0;i<opts.length;i++){
    v = opts[i];
    html += '<button class="vopt' + (i === cur ? ' selected' : '') + '" type="button" data-idx="' + i + '">'
          + '<span><span class="vname">' + v.name + '</span>'
          + '<span class="vform">' + v.form + '</span>'
          + '<span class="vnotes">構成音 ' + v.notes + '</span>'
          + '<span class="vsrc">' + v.src + '／' + v.strings + '弦・押弦' + v.fingers + '本</span>'
          + (i === cur ? '<span class="vsel">現在の選択</span>' : '')
          + '</span><span>' + diagram(v.form) + '</span></button>';
  }
  voiceBox.innerHTML = html;
  var btns = voiceBox.querySelectorAll('.vopt'), k;
  for(k=0;k<btns.length;k++){
    btns[k].addEventListener('click', onPick, false);
  }
}
function onPick(ev){
  var idx = parseInt(this.getAttribute('data-idx'), 10);
  selected[sheetChord] = idx;
  store.set(STORE_PREFIX + sheetChord, idx);
  store.set(STAMP_KEY, new Date().toISOString());
  mark('b4', true, '④ 候補を選ぶ → ダイアグラムが即時に変わった（' + sheetChord + ' = '
       + voicings[sheetChord][idx].form + '）', 't4');
  redraw(true);
  paintOptions(sheetChord);
}
function showSheet(){
  scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
  scrim.className = 'scrim open';
  sheet.className = 'sheet open';
  document.body.style.position = 'fixed';
  document.body.style.top = (-scrollY) + 'px';
  document.body.style.width = '100%';
}
function openLyricSheet(mi){
  sheetMode = 'lyric'; sheetMi = mi; sheetChord = null;
  var m = measures[mi], names = [], i;
  for(i = 0; i < m.chords.length; i++){ names.push(m.chords[i][0]); }
  document.getElementById('sheetTitle').textContent = 'M' + (mi + 1) + ' の歌詞';
  document.getElementById('sheetNote').innerHTML =
    m.section + (m.cue ? ' \\u30fb ' + m.cue : '') + ' \\u30fb ' + names.join(' / ')
    + '<br>この端末にだけ保存されます。空にすれば削除されます。';
  document.getElementById('voiceOptions').innerHTML =
    '<textarea class="lyricEditBox" id="lyricEdit"></textarea>'
    + '<div class="lyricRow"><button class="ctrl sm" id="lyricSaveOne" type="button">保存</button>'
    + '<button class="ctrl alt sm" id="lyricCancel" type="button">やめる</button></div>';
  document.getElementById('lyricEdit').value = lyricOf(mi);
  document.getElementById('lyricSaveOne').addEventListener('click', function(){
    var v = document.getElementById('lyricEdit').value.replace(/^\s+|\s+$/g, '');
    if(v === ''){ delete lyrics[String(mi)]; } else { lyrics[String(mi)] = v; }
    saveLyrics(); paintScoreLyrics(); paintLyricStat(); redraw(true); closeSheet();
  }, false);
  document.getElementById('lyricCancel').addEventListener('click', closeSheet, false);
  showSheet();
}
function openSheet(chord){
  sheetMode = 'voicing'; sheetMi = -1;
  sheetChord = chord;
  document.getElementById('sheetTitle').textContent = chord + ' のフォーム';
  document.getElementById('sheetNote').innerHTML =
    '表示するフォームを選びます。選択は同じコード名の全出現箇所に適用され、この端末に保存されます。<br>'
    + '掲載フォームは構成音を機械検証済み（押弦4本以内・4フレット幅以内）。';
  paintOptions(chord);
  showSheet();
  var n = (voicings[chord] && voicings[chord].length) || 0;
  if(n > 0){
    mark('b3', true, '③ ' + chord + ' をタップ → 候補 ' + n + '件を表示', 't3');
  } else {
    /* N.C. などフォームを持たないコード。仕様どおりなので NG にはしない */
    document.getElementById('t3').innerHTML =
      '③ コードカードをタップ → 候補が出る（' + chord
      + ' はフォームを持たないコードです。別のカードで試してください）';
  }
}
function closeSheet(){
  scrim.className = 'scrim';
  sheet.className = 'sheet';
  document.body.style.position = '';
  document.body.style.top = '';
  document.body.style.width = '';
  window.scrollTo(0, scrollY);
}
scrim.addEventListener('click', closeSheet, false);
document.getElementById('closeSheet').addEventListener('click', closeSheet, false);

function bindCard(el){
  el.addEventListener('click', function(){
    openSheet(el.getAttribute('data-chord'));
  }, false);
}
bindCard(cards.current); bindCard(cards.next); bindCard(cards.after);

(function(){
  var minis = document.querySelectorAll('.mini[data-mi]'), i;
  function bindMini(el){
    el.addEventListener('click', function(){
      openLyricSheet(parseInt(el.getAttribute('data-mi'), 10));
    }, false);
  }
  for(i = 0; i < minis.length; i++){ bindMini(minis[i]); }
})();

/* ---------- 再生カーソル ---------- */
var pos = 0, playing = false, startT = 0, rafId = 0, lastMi = -1;
function locate(bp){
  var acc = 0, i, e;
  for(i=0;i<seq.length;i++){
    e = acc + seq[i].beats;
    if(bp < e || i === seq.length - 1){ return {i:i, local:Math.max(0, bp - acc)}; }
    acc = e;
  }
  return {i:0, local:0};
}
function fmtTime(ms){
  var s = Math.floor(ms/1000), m = Math.floor(s/60);
  s = s % 60;
  return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
}
var loc = {i:0, local:0}, lastSeqI = -1;
function redraw(force){
  var x = seq[loc.i],
      n = seq[Math.min(loc.i+1, seq.length-1)],
      a = seq[Math.min(loc.i+2, seq.length-1)],
      m = measures[x.mi], el, olds, k;
  /* カードの再描画はコードが変わったときだけ（毎フレームやると実機で重い） */
  if(force || lastSeqI !== loc.i){
    lastSeqI = loc.i;
    renderCard(cards.current, x.chord);
    renderCard(cards.next, n.chord);
    renderCard(cards.after, a.chord);
    document.getElementById('sectionTitle').textContent = m.section + (m.cue ? ' \\u30fb ' + m.cue : '');
    var lt = lyricOf(x.mi);
    document.getElementById('lyric').innerHTML =
      (lt ? esc(lt) : '<span style="color:#bbb">' + esc(m.lyric) + '</span>')
      + '<small>' + m.meter + ' \\u30fb M' + (x.mi+1) + '</small>';
    if(lastMi !== x.mi){
      olds = document.querySelectorAll('.mini.activeMeasure');
      for(k=0;k<olds.length;k++){ olds[k].className = 'mini'; }
      el = document.querySelector('.mini[data-mi="' + x.mi + '"]');
      if(el){ el.className = 'mini activeMeasure'; }
      lastMi = x.mi;
    }
  }
  document.getElementById('codebar').style.width = (Math.min(1, loc.local / x.beats) * 100) + '%';
}
function tick(ms){
  var t = Math.min(ms, duration);
  loc = locate(t / BEATMS);
  redraw(false);
  document.getElementById('songbar').style.width = (t / duration * 100) + '%';
  document.getElementById('time').textContent = fmtTime(t);
  if(playing){
    pos = (new Date().getTime()) - startT;
    if(pos >= duration){
      pos = duration; playing = false;
      document.getElementById('play').textContent = '\\u25b6 再生';
    } else {
      rafId = window.requestAnimationFrame ?
        window.requestAnimationFrame(function(){ tick((new Date().getTime()) - startT); }) :
        window.setTimeout(function(){ tick((new Date().getTime()) - startT); }, 50);
    }
  }
}
document.getElementById('play').addEventListener('click', function(){
  if(!playing){
    if(pos >= duration){ pos = 0; }
    playing = true;
    startT = (new Date().getTime()) - pos;
    this.textContent = '\\u2016 一時停止';
    tick(pos);
  } else {
    playing = false;
    pos = (new Date().getTime()) - startT;
    if(window.cancelAnimationFrame){ window.cancelAnimationFrame(rafId); }
    this.textContent = '\\u25b6 再生';
    tick(pos);
  }
}, false);
document.getElementById('reset').addEventListener('click', function(){
  playing = false;
  if(window.cancelAnimationFrame){ window.cancelAnimationFrame(rafId); }
  pos = 0; lastMi = -1; lastSeqI = -1;
  document.getElementById('play').textContent = '\\u25b6 再生';
  tick(0);
}, false);

/* ---------- 受入テスト表示 ---------- */
function mark(id, ok, text, textId){
  var b = document.getElementById(id);
  b.className = 'badge ' + (ok ? 'ok' : 'ng');
  b.textContent = ok ? 'OK' : 'NG';
  if(text && textId){ document.getElementById(textId).innerHTML = text; }
}
function wait(id){
  var b = document.getElementById(id);
  b.className = 'badge wait';
  b.textContent = '未';
}
mark('b1', true);
mark('b2', store.usable());
if(!store.usable()){
  document.getElementById('b2').textContent = 'NG';
}
wait('b3'); wait('b4');
if(restored.length){
  var at = store.get(STAMP_KEY);
  mark('b5', true, '⑤ 再読み込み後も選択が残っている：<b>' + restored.join(' / ') + '</b>'
       + (at ? '<br><span style="color:#888">保存時刻 ' + at + '</span>' : ''), 't5');
} else {
  wait('b5');
  document.getElementById('t5').innerHTML =
    '⑤ 再読み込み後も選択が残っている（まだ保存された選択はありません）';
}
if(restored.length){
  document.getElementById('hint').innerHTML =
    '③④は読み込みのたびに「未」へ戻ります（今回のタップ待ちという意味で、失敗ではありません）。'
    + '<b>⑤が緑なら、前回選んだフォームが再読み込み後も保持されています。</b>';
}
document.getElementById('lyricApply').addEventListener('click', function(){
  var ta = document.getElementById('lyricInput'),
      startEl = document.getElementById('lyricStart'),
      start = parseInt(startEl.value, 10),
      res, k;
  if(isNaN(start) || start < 1){ start = 1; }
  if(start > measures.length){ start = measures.length; }
  res = parseLyricText(ta.value, start);
  if(res.mode === 'empty'){
    document.getElementById('lyricStat').innerHTML = '取り込む歌詞がありません';
    return;
  }
  for(k in res.map){ if(res.map.hasOwnProperty(k)){ lyrics[k] = res.map[k]; } }
  saveLyrics(); paintScoreLyrics(); redraw(true); paintLyricStat();
  document.getElementById('lyricStat').innerHTML +=
    '　/　今回 <b>' + res.count + '</b> 小節を取り込みました（'
    + (res.mode === 'numbered' ? '小節番号つきとして読み取り' : 'M' + start + ' から順に割り当て') + '）';
  ta.value = '';
}, false);
document.getElementById('lyricExport').addEventListener('click', function(){
  var t = exportLyricText(), ta = document.getElementById('lyricInput');
  if(t === ''){
    document.getElementById('lyricStat').innerHTML = '書き出す歌詞がありません';
    return;
  }
  ta.value = t;
  try { ta.focus(); ta.setSelectionRange(0, t.length); } catch(e) {}
  document.getElementById('lyricStat').innerHTML =
    '上の欄に書き出しました。長押しして<b>すべてを選択→コピー</b>で控えを取れます';
}, false);
document.getElementById('lyricClear').addEventListener('click', function(){
  var k;
  for(k in lyrics){ if(lyrics.hasOwnProperty(k)){ delete lyrics[k]; } }
  store.remove(LYRIC_KEY);
  paintScoreLyrics(); redraw(true); paintLyricStat();
}, false);
paintScoreLyrics(); paintLyricStat();

document.getElementById('btnReload').addEventListener('click', function(){
  window.location.reload();
}, false);
document.getElementById('btnClear').addEventListener('click', function(){
  /* 受入テスト用。フォーム選択だけを消し、入力した歌詞は消さない */
  store.clearAll();
  window.location.reload();
}, false);
document.getElementById('stamp').textContent = 'v12 PoC \\u30fb 保存' + (store.usable() ? '有効' : '一時');

tick(0);
window.__poc = {
  openSheet: openSheet, closeSheet: closeSheet, selected: selected,
  voicings: voicings, diagram: diagram, store: store, restored: restored,
  openLyricSheet: openLyricSheet, lyrics: lyrics, lyricOf: lyricOf,
  parseLyricText: parseLyricText, exportLyricText: exportLyricText,
  measures: measures
};
})();
</script>
</body>
</html>
'''

out = (TPL.replace('__MEASURES__', json.dumps(measures, ensure_ascii=False))
          .replace('__VOICINGS__', json.dumps(voicings, ensure_ascii=False))
          .replace('__SCORE__', score_html)
          .replace('__CARDS__', cards_html)
          .replace('__SECTION__', measures[0]['section'])
          .replace('__LYRIC__', measures[0]['lyric'])
          .replace('__METER__', measures[0]['meter'] + ' ・ M1'))

io.open(os.path.join(ROOT, 'aliens', 'index.html'), 'w', encoding='utf-8').write(out)
print('written bytes:', len(out.encode('utf-8')))
print('chords used:', len(used), 'missing voicings:', missing)
