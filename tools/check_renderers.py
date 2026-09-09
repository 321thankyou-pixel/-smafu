# -*- coding: utf-8 -*-
"""静的HTML用 diagram_html(Python) と 動的用 diagram(JS) が
全フォームで同一出力になることを確認する。"""
import io, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_app  # 生成も兼ねる（副作用で aliens/index.html を書き出す）

voicings = json.load(io.open(os.path.join(HERE, 'voicings.json'), encoding='utf-8'))
forms = []
for c in sorted(voicings):
    for o in voicings[c]:
        forms.append((c, o['form']))

html = io.open(os.path.join(os.path.dirname(HERE), 'aliens', 'index.html'), encoding='utf-8').read()
js = re.search(r'function parseForm\(form\)\{.*?\n\}\nfunction diagram\(form\)\{.*?\n\}\n', html, re.S).group(0)
script = js + '''
var out = {};
var list = %s;
for (var i = 0; i < list.length; i++) { out[list[i]] = diagram(list[i]); }
console.log(JSON.stringify(out));
''' % json.dumps([f for _, f in forms])
res = subprocess.run(['node', '-e', script], capture_output=True, text=True)
if res.returncode:
    print(res.stderr); sys.exit(2)
jsout = json.loads(res.stdout)

def norm(h):
    return (h.replace('&times;', '×').replace('&#9675;', '○')
             .replace('\\u00d7', '×').replace('\\u25cb', '○')
             .replace('\\u301c', '〜'))

bad = []
for c, f in forms:
    a = norm(build_app.diagram_html(f))
    b = norm(jsout[f])
    if a != b:
        bad.append((c, f, a, b))
print('照合フォーム数:', len(forms))
if bad:
    for c, f, a, b in bad[:3]:
        print('MISMATCH', c, f); print(' py:', a[:300]); print(' js:', b[:300])
    sys.exit(1)
print('PASS: 2つのレンダラの出力は全フォームで一致')

# ナット表示の確認: 開放弦があり、かつ押弦が5フレット以内なら必ずナットから描く
def vals_of(f):
    parts = f.split('-') if '-' in f else list(f)
    return ['x' if p.lower() == 'x' else int(p) for p in parts]

nut = set(f for _, f in forms if 'nut' in norm(jsout[f]))
should = []
for _, f in forms:
    v = vals_of(f)
    fr = [x for x in v if isinstance(x, int) and x > 0]
    if any(x == 0 for x in v) and fr and max(fr) <= 5:
        should.append(f)
missing = [f for f in should if f not in nut]
extra = []
for _, f in forms:
    if f in nut:
        v = vals_of(f)
        fr = [x for x in v if isinstance(x, int) and x > 0]
        if fr and min(fr) - 1 > 4:
            extra.append(f)
print('ナット付き:', len(nut), '/ ナット必須:', len(should))
print('ナットが出るべきなのに出ない:', missing)
print('ナットが出てはいけないのに出る:', extra)

# 窓外に描かれるドットが無いこと
outside = [f for _, f in forms
           if 'left:-' in jsout[f] or re.search(r'left:1[0-9][0-9]\.', jsout[f])]
print('窓外にドットが出るフォーム:', outside)
sys.exit(1 if (missing or extra or outside) else 0)
