# -*- coding: utf-8 -*-
"""定番フォームを候補として与え、構成音を機械検証して採用する。
検証を通らないものは捨て、足りない分だけ探索で補う。"""
import json, itertools, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_voicings import DEFS, check, fmt, OPEN, PC, pcs, analyze

MAXF = 12

# 定番として与える候補（6弦->1弦）。検証を通ったものだけ採用される。
SEEDS = {
 'BbM7':      ['x13231','6-8-7-7-6-6','x-x-8-7-6-5','x-1-3-2-3-1'],
 'BbM9':      ['x-1-0-2-1-1','x13233','6-8-7-7-8-x'],
 'BbmM7':     ['x13221','6-8-7-6-6-6','x-x-8-6-6-5'],
 'BbmM7(13)': ['x13223','6-8-7-6-8-6','x-1-3-2-4-1'],
 'Bbm6':      ['x13121','6-x-5-6-6-x','x-1-3-1-2-x'],
 'A7':        ['x02020','x02223','5-7-5-6-5-5'],
 'Aaug7':     ['x01021','5-x-5-6-6-5','x-0-1-0-2-1'],
 'Aaug7(b9)': ['x01011','5-4-5-6-6-5','x-0-1-0-1-1'],
 'Aaug7(#9)': ['x01031','5-6-5-6-6-x','x-0-1-0-3-1'],
 'Am7':       ['x02010','5-7-5-5-5-5','x-0-5-5-5-x'],
 'Am7/D':     ['x-x-0-5-5-5','5-x-5-5-5-x','x-x-0-2-1-0'],
 'G#7':       ['4-6-4-5-4-4','x-11-10-11-9-11','4-x-4-5-4-x'],
 'Gm7':       ['3-5-3-3-3-3','3-x-3-3-3-x','x-10-8-10-10-10'],
 'G7':        ['320001','3-5-3-4-3-3','3-x-3-4-3-x'],
 'G7(13)':    ['3-x-3-4-5-x','3-5-3-4-5-3','320003'],
 'FM7':       ['xx3210','1-x-2-2-1-0','1-3-3-2-1-1'],
 'F9':        ['1-3-1-2-1-3','1-x-1-2-1-3','x-8-7-8-8-8'],
 'F9(13)':    ['1-3-1-2-3-3','1-x-1-2-3-x','x-8-7-8-10-8'],
 'F7/C':      ['x-3-1-2-1-1','x-3-3-2-4-1','x-x-3-2-4-1'],
 'Em7':       ['020000','0-2-2-0-3-0','x-7-9-7-8-7'],
 'Em11':      ['000000','0-2-2-0-0-0','0-x-0-0-0-0'],
 'Em7/A':     ['x-0-2-0-3-0','x-0-2-2-0-0','5-x-5-4-5-x'],
 'E7':        ['020100','0-7-6-7-0-0','x-7-6-7-5-7'],
 'E7(b9)':    ['0-x-0-1-0-1','020101','x-7-6-7-8-7'],
 'E(b9)/G#':  ['4-x-2-1-0-0','4-7-6-7-x-x','x-x-2-1-0-3'],
 'Dm7':       ['xx0211','x-5-7-5-6-5','10-12-10-10-10-10'],
 'Dm9':       ['x-5-3-5-5-5','x-5-5-5-5-x','x-x-0-2-1-0'],
 'D7':        ['xx0212','x-5-4-5-3-5','5-x-4-5-3-x'],
 'D9':        ['x-5-4-5-5-x','x-5-4-5-5-5','10-x-10-11-10-12'],
 'D#9':       ['x-6-5-6-6-6','x-6-5-6-6-x','11-x-11-12-11-13'],
 'Cm7':       ['x-3-5-3-4-3','8-10-8-8-8-8','x-3-1-3-4-x'],
 'C9':        ['x-3-2-3-3-3','8-x-8-7-9-8','x-3-2-3-3-x'],
 'C9sus4':    ['x-3-3-3-3-3','x-3-3-3-3-x','8-x-8-8-8-8'],
 'Csus4/A':   ['x-0-3-0-1-1','x-0-3-0-1-3','5-x-5-5-6-x'],
 'C/Bb':      ['x-1-2-0-1-0','6-x-5-5-5-x','x-1-2-2-1-0'],
 'C/D':       ['x-x-0-0-1-0','x-5-5-5-5-3','10-x-10-9-8-x'],
 'Bm7-5':     ['x-2-3-2-3-x','7-x-7-6-7-x','x-2-0-2-0-x'],
}

def parse(s):
    if '-' in s:
        parts = s.split('-')
    else:
        parts = list(s)
    out = []
    for p in parts:
        out.append('x' if p.lower() == 'x' else int(p))
    assert len(out) == 6, s
    return out

def span_of(form):
    fr = [v for v in form if isinstance(v, int) and v > 0]
    return (max(fr) - min(fr)) if fr else 0

def minfret(form):
    fr = [v for v in form if isinstance(v, int) and v > 0]
    return min(fr) if fr else 0

def bucket(form):
    mf = minfret(form)
    if mf <= 1: return 0
    if mf <= 4: return 1
    return 2

def score(form, info):
    opens = sum(1 for v in form if v == 0)
    mixed = 3 if (minfret(form) >= 5 and opens > 0) else 0
    return (info['fingers'], span_of(form), mixed, -info['strings'], minfret(form))

def search(spec):
    root, allow, req, bass = spec
    allowed = set(pcs(root, allow))
    if bass: allowed.add(PC[bass])
    per = [[f for f in range(0, MAXF + 1) if (OPEN[i] + f) % 12 in allowed] for i in range(6)]
    res = []
    for start in range(0, 3):
        for end in range(start + 3, 6):
            n = end - start + 1
            for combo in itertools.product(*[per[start + k] for k in range(n)]):
                fr = [c for c in combo if c > 0]
                if fr and max(fr) - min(fr) > 3: continue
                form = ['x'] * 6
                for k in range(n): form[start + k] = combo[k]
                info = check(form, spec)
                if info: res.append((form, info))
    return res

POSNAME = {0: 'ロー', 1: 'ミドル', 2: 'ハイ'}

def pick_spread(cands, taken):
    """minfret が近すぎるものを避けて最大3つ選ぶ。cands は (form, info) の優先順リスト。"""
    for f, info in cands:
        if len(taken) >= 3:
            break
        if any(fmt(f) == fmt(t[0]) for t in taken):
            continue
        if any(abs(minfret(f) - minfret(t[0])) < 2 for t in taken):
            continue
        taken.append((f, info))
    return taken

result = {}
report = []
for chord in sorted(DEFS):
    spec = DEFS[chord]
    rejected = []
    seed_ok = []
    for st in SEEDS.get(chord, []):
        f = parse(st)
        info = check(f, spec)
        if not info:
            rejected.append(st)
            continue
        seed_ok.append((f, info))
    seed_ok.sort(key=lambda t: (bucket(t[0]), score(t[0], t[1])))
    taken = pick_spread(seed_ok, [])
    srcs = ['定番形'] * len(taken)
    if len(taken) < 3:
        cands = [(f, i) for f, i in search(spec)
                 if not (minfret(f) >= 5 and any(v == 0 for v in f))]
        cands.sort(key=lambda t: (bucket(t[0]), score(t[0], t[1])))
        before = len(taken)
        taken = pick_spread(cands, taken)
        srcs += ['探索'] * (len(taken) - before)
    opts = []
    for (f, info), src in zip(taken, srcs):
        mf = minfret(f)
        opts.append({'name': ('オープン' if mf == 0 else str(mf) + 'F ' + POSNAME[bucket(f)]),
                     'form': fmt(f), 'frets': f, 'src': src,
                     'strings': info['strings'], 'fingers': info['fingers']})
    result[chord] = opts
    report.append((chord, [o['form'] for o in opts], [o['src'] for o in opts], rejected))

json.dump(result, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voicings.json'), 'w'), ensure_ascii=False, indent=1)
for c, forms, srcs, rej in report:
    print('%-12s %-38s %-20s reject:%s' % (c, ','.join(forms), ','.join(srcs), ','.join(rej)))
print('---')
print('chords:', len(result), ' options total:', sum(len(v) for v in result.values()))
print('chords with <2 options:', [c for c, v in result.items() if len(v) < 2])
