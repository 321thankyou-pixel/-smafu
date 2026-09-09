# -*- coding: utf-8 -*-
"""定番フォームを候補として与え、構成音を機械検証して採用する。
検証を通らないものは捨て、足りない分だけ探索で補う。"""
import json, itertools, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_voicings import DEFS, check, fmt, OPEN, PC, pcs, analyze

MAXF = 12

# 定番として与える候補（6弦->1弦）。検証を通ったものだけ採用される。
SEEDS = {
 'CM7':       ['x32000','x35453','x32003','8-10-9-9-8-8','x-x-10-9-8-7','x-x-10-12-12-12'],
 'CM9':       ['x30000','x-3-2-4-3-x','8-10-9-9-10-x','x-3-5-4-5-5'],
 'CmM7':      ['x31003','x35443','8-10-9-8-8-8'],
 'CmM7(13)':  ['x31203','x35443','8-10-9-8-10-8','x-3-1-2-1-3'],
 'Cm6':       ['x31213','x-3-5-3-4-x','8-x-7-8-8-x'],
 'B7':        ['x21202','797877','x24242','7-9-7-8-7-7'],
 'Baug7':     ['x21203','7-10-7-8-8-7','x-2-1-2-0-3'],
 'Baug7(b9)': ['x21203','x-2-1-2-0-3','7-6-7-8-8-7','x-2-1-2-1-3'],
 'Baug7(#9)': ['x-2-1-2-3-3','7-8-7-8-8-x','x-2-1-2-3-x','7-x-7-8-8-7'],
 'Em9':       ['020002','x-7-5-7-7-x','0-2-2-0-0-2','x-7-5-7-7-x'],
 'Em7':       ['020000','022030','x79787','079800'],
 'E7':        ['020100','020130','x79797','076700'],
 'E9':        ['020102','x76777','076770'],
 'A7':        ['x02020','x02223','5-7-5-6-5-5','x-12-11-12-x-x'],
 'A7(13)':    ['x02022','5-7-5-6-7-5','x-0-2-0-2-2','x-12-11-12-14-x'],
 'Am7':       ['x02010','575555','x05555','x02013'],
 'Bm7':       ['x24232','797777','x2423x','x24242'],
 'Bb7':       ['x13131','686766','x-1-3-1-3-1'],
 'F9':        ['1-3-1-2-1-3','x-8-7-8-8-8','1-x-1-2-1-3','x87888'],
 'G9':        ['3-x-3-4-3-5','353435','3-5-3-4-3-5','x-10-9-10-10-10'],
 'G9(13)':    ['3-x-3-4-5-5','3-5-3-4-5-5','x-10-9-10-12-12'],
 'GM7':       ['320002','3-5-4-4-3-3','x-10-12-11-12-x','x-x-5-4-3-2'],
 'Dm7':       ['xx0211','x57565','10-12-10-10-10-10','x-5-7-5-6-5'],
 'D9':        ['x-5-4-5-5-x','x-5-4-5-5-5','10-x-10-11-10-12'],
 'D9sus4':    ['x-5-5-5-5-5','x-5-5-5-5-x','10-x-10-10-10-10','x-5-5-5-5-3'],
 'C#m7-5':    ['x4545x','x45450','9-10-9-9-x-x','x-4-5-4-5-x'],
 'F#7':       ['242322','x98980','2-4-2-3-2-2'],
 'F#7(b9)':   ['2-x-2-3-2-3','2-4-2-3-2-3','x-9-8-9-8-9'],
 'F#m7':      ['242222','x-9-11-9-10-9','2-4-2-2-2-2'],
 'F#m11':     ['222222','x-9-11-9-12-9','2-2-2-2-2-2'],
 'Dsus4/B':   ['x-2-0-0-3-3','x20033','7-x-7-7-8-x','x-2-0-0-3-0'],
 'D/C':       ['x30232','x-3-0-2-3-2','8-x-7-7-7-x'],
 'D/E':       ['000232','0-x-0-7-7-5','0-x-0-11-10-10'],
 'G7/D':      ['x-5-3-4-3-3','x53003','x-x-0-0-0-1','10-x-10-10-12-10'],
 'Bm7/E':     ['0x0202','000202','0-2-0-2-0-0','x-7-9-7-7-7'],
 'F#m7/B':    ['7-9-7-9-x-x','x-2-4-2-2-2','7-9-9-9-10-9','x22222'],
 'F#(b9)/Bb': ['6-x-4-3-2-2','6-8-6-6-7-x','x-1-4-3-2-2','6-x-8-6-7-x'],
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
