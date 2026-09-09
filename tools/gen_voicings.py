# -*- coding: utf-8 -*-
"""エイリアンズで使う全コードのギターフォームを探索し、構成音を検証して出力する。
検証内容: 鳴る全弦の音名がそのコードの構成音に含まれ、必須音がすべて揃い、
        オンコード指定があれば最低音が指定ベース音であること。
"""
import json, itertools, os, sys

OPEN = [4, 9, 2, 7, 11, 4]   # 6弦->1弦 E A D G B E
NAME = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
      'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}

def pcs(root, intervals):
    r = PC[root]
    return [(r + i) % 12 for i in intervals]

# chord -> (allowed intervals, required intervals, bass note or None)
# 1=root, 3=m3, 4=M3, 6=b5, 7=P5, 8=#5, 9=b7? -- 半音で書く
R, m3, M3, P4, b5, P5, s5, M6, m7, M7 = 0, 3, 4, 5, 6, 7, 8, 9, 10, 11
b9, n9, s9, n11, n13 = 1, 2, 3, 5, 9

DEFS = {
  'CM7':        ('C', [R,M3,P5,M7],        [R,M3,M7],        None),
  'CM9':        ('C', [R,M3,P5,M7,n9],     [R,M3,M7,n9],     None),
  'CmM7':       ('C', [R,m3,P5,M7],        [R,m3,M7],        None),
  'CmM7(13)':   ('C', [R,m3,P5,M7,n13],    [R,m3,M7,n13],    None),
  'Cm6':        ('C', [R,m3,P5,M6],        [R,m3,M6],        None),
  'B7':         ('B', [R,M3,P5,m7],        [R,M3,m7],        None),
  'Baug7':      ('B', [R,M3,s5,m7],        [R,M3,s5,m7],     None),
  'Baug7(b9)':  ('B', [R,M3,s5,m7,b9],     [R,M3,s5,m7,b9],  None),
  'Baug7(#9)':  ('B', [R,M3,s5,m7,s9],     [R,M3,s5,m7,s9],  None),
  'Em9':        ('E', [R,m3,P5,m7,n9],     [R,m3,m7,n9],     None),
  'Em7':        ('E', [R,m3,P5,m7],        [R,m3,m7],        None),
  'E7':         ('E', [R,M3,P5,m7],        [R,M3,m7],        None),
  'E9':         ('E', [R,M3,P5,m7,n9],     [R,M3,m7,n9],     None),
  'A7':         ('A', [R,M3,P5,m7],        [R,M3,m7],        None),
  'A7(13)':     ('A', [R,M3,P5,m7,n13],    [R,M3,m7,n13],    None),
  'Am7':        ('A', [R,m3,P5,m7],        [R,m3,m7],        None),
  'Bm7':        ('B', [R,m3,P5,m7],        [R,m3,m7],        None),
  'Bb7':        ('A#',[R,M3,P5,m7],        [R,M3,m7],        None),
  'F9':         ('F', [R,M3,P5,m7,n9],     [R,M3,m7,n9],     None),
  'G9':         ('G', [R,M3,P5,m7,n9],     [R,M3,m7,n9],     None),
  'G9(13)':     ('G', [R,M3,P5,m7,n9,n13], [R,M3,m7,n9,n13], None),
  'GM7':        ('G', [R,M3,P5,M7],        [R,M3,M7],        None),
  'Dm7':        ('D', [R,m3,P5,m7],        [R,m3,m7],        None),
  'D9':         ('D', [R,M3,P5,m7,n9],     [R,M3,m7,n9],     None),
  'D9sus4':     ('D', [R,P4,P5,m7,n9],     [R,P4,m7,n9],     None),
  'C#m7-5':     ('C#',[R,m3,b5,m7],        [R,m3,b5,m7],     None),
  'F#7':        ('F#',[R,M3,P5,m7],        [R,M3,m7],        None),
  'F#7(b9)':    ('F#',[R,M3,P5,m7,b9],     [R,M3,m7,b9],     None),
  'F#m7':       ('F#',[R,m3,P5,m7],        [R,m3,m7],        None),
  'F#m11':      ('F#',[R,m3,P5,m7,n11],    [R,m3,m7,n11],    None),
  # オンコード
  'Dsus4/B':    ('D', [R,P4,P5],           [R,P4],           'B'),
  'D/C':        ('D', [R,M3,P5],           [R,M3],           'C'),
  'D/E':        ('D', [R,M3,P5],           [R,M3],           'E'),
  'G7/D':       ('G', [R,M3,P5,m7],        [R,M3,m7],        'D'),
  'Bm7/E':      ('B', [R,m3,P5,m7],        [R,m3,m7],        'E'),
  'F#m7/B':     ('F#',[R,m3,P5,m7],        [R,m3,m7],        'B'),
  'F#(b9)/Bb':  ('F#',[R,M3,P5,b9],        [R,M3,b9],        'A#'),
}

MAXF = 14

def fingers_needed(form):
    """form: 6要素(6弦->1弦), 'x' か int。押弦に必要な指の本数を見積る。足りなければ None"""
    fr = [(i, v) for i, v in enumerate(form) if isinstance(v, int) and v > 0]
    if not fr:
        return 0
    frets = [v for _, v in fr]
    lo, hi = min(frets), max(frets)
    if hi - lo > 3:
        return None
    plain = len(fr)
    if plain <= 4:
        return plain
    # セーハを検討: 最低フレットで全弦を押さえる
    # セーハ下に開放弦があると不可
    lo_idx = min(i for i, v in enumerate(form) if v != 'x')
    for i in range(lo_idx, 6):
        if form[i] == 0:
            return None
    barre = 1 + sum(1 for _, v in fr if v > lo)
    return barre if barre <= 4 else None

def analyze(form):
    out = []
    for i, v in enumerate(form):
        if v == 'x':
            continue
        out.append((i, (OPEN[i] + v) % 12))
    return out

def check(form, spec):
    root, allow, req, bass = spec
    allowed = set(pcs(root, allow))
    required = set(pcs(root, req))
    if bass:
        allowed.add(PC[bass])
    snd = analyze(form)
    if len(snd) < 4:
        return None
    # 内部ミュートは「6弦が鳴っていて5弦だけ抜く」形のみ許可
    idxs = [i for i, _ in snd]
    if idxs != list(range(idxs[0], idxs[-1] + 1)):
        if not (idxs[0] == 0 and idxs[1:] == list(range(2, idxs[-1] + 1))):
            return None
    got = set(p for _, p in snd)
    if not got.issubset(allowed):
        return None
    if not required.issubset(got):
        return None
    if bass:
        if snd[0][1] != PC[bass]:
            return None
    else:
        if snd[0][1] != PC[root]:
            return None
    f = fingers_needed(form)
    if f is None:
        return None
    return {'strings': len(snd), 'fingers': f,
            'minfret': min([v for v in form if isinstance(v, int) and v > 0] or [0])}

def search(spec):
    root, allow, req, bass = spec
    allowed = set(pcs(root, allow))
    if bass:
        allowed.add(PC[bass])
    per = []
    for i in range(6):
        per.append([f for f in range(0, MAXF + 1) if (OPEN[i] + f) % 12 in allowed])
    res = []
    for start in range(0, 3):
        for end in range(start + 3, 6):
            n = end - start + 1
            for combo in itertools.product(*[per[start + k] for k in range(n)]):
                frets = [c for c in combo if c > 0]
                if frets and max(frets) - min(frets) > 3:
                    continue
                form = ['x'] * 6
                for k in range(n):
                    form[start + k] = combo[k]
                info = check(form, spec)
                if info:
                    res.append((form, info))
    return res

def fmt(form):
    if all(v == 'x' or v < 10 for v in form):
        return ''.join('x' if v == 'x' else str(v) for v in form)
    return '-'.join('x' if v == 'x' else str(v) for v in form)

def pick(chord, spec):
    cands = search(spec)
    if not cands:
        return []
    # 位置帯ごとに最良を選ぶ
    def score(item):
        form, info = item
        frets = [v for v in form if isinstance(v, int) and v > 0]
        span = (max(frets) - min(frets)) if frets else 0
        opens = sum(1 for v in form if v == 0)
        return (-info['strings'], info['fingers'], span, -opens, info['minfret'])
    buckets = {}
    for form, info in cands:
        mf = info['minfret']
        b = 0 if mf <= 4 else (1 if mf <= 8 else 2)
        buckets.setdefault(b, []).append((form, info))
    out = []
    for b in sorted(buckets):
        best = sorted(buckets[b], key=score)[0]
        out.append(best)
    return out

if __name__ == '__main__':
    result = {}
    for chord in sorted(DEFS):
        opts = pick(chord, DEFS[chord])
        result[chord] = [{'form': fmt(f), 'strings': i['strings'],
                          'fingers': i['fingers'], 'minfret': i['minfret']} for f, i in opts]
        print(chord, [o['form'] for o in result[chord]], file=sys.stderr)
    json.dump(result, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voicings_raw.json'), 'w'), ensure_ascii=False, indent=1)
