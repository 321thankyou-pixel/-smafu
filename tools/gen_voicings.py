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
  'BbM7':       ('Bb', [R,M3,P5,M7],        [R,M3,M7], None),
  'BbM9':       ('Bb', [R,M3,P5,M7,n9],     [R,M3,M7,n9], None),
  'BbmM7':      ('Bb', [R,m3,P5,M7],        [R,m3,M7], None),
  'BbmM7(13)':  ('Bb', [R,m3,P5,M7,n13],    [R,m3,M7,n13], None),
  'Bbm6':       ('Bb', [R,m3,P5,M6],        [R,m3,M6], None),
  'A7':         ('A', [R,M3,P5,m7],        [R,M3,m7], None),
  'Aaug7':      ('A', [R,M3,s5,m7],        [R,M3,s5,m7], None),
  'Aaug7(b9)':  ('A', [R,M3,s5,m7,b9],     [R,M3,s5,m7,b9], None),
  'Aaug7(#9)':  ('A', [R,M3,s5,m7,s9],     [R,M3,s5,m7,s9], None),
  'Dm9':        ('D', [R,m3,P5,m7,n9],     [R,m3,m7,n9], None),
  'Dm7':        ('D', [R,m3,P5,m7],        [R,m3,m7], None),
  'D7':         ('D', [R,M3,P5,m7],        [R,M3,m7], None),
  'D9':         ('D', [R,M3,P5,m7,n9],     [R,M3,m7,n9], None),
  'G7':         ('G', [R,M3,P5,m7],        [R,M3,m7], None),
  'G7(13)':     ('G', [R,M3,P5,m7,n13],    [R,M3,m7,n13], None),
  'Gm7':        ('G', [R,m3,P5,m7],        [R,m3,m7], None),
  'Am7':        ('A', [R,m3,P5,m7],        [R,m3,m7], None),
  'G#7':        ('G#',[R,M3,P5,m7],        [R,M3,m7], None),
  'D#9':        ('D#', [R,M3,P5,m7,n9],     [R,M3,m7,n9], None),
  'F9':         ('F', [R,M3,P5,m7,n9],     [R,M3,m7,n9], None),
  'F9(13)':     ('F', [R,M3,P5,m7,n9,n13], [R,M3,m7,n9,n13], None),
  'FM7':        ('F', [R,M3,P5,M7],        [R,M3,M7], None),
  'Cm7':        ('C', [R,m3,P5,m7],        [R,m3,m7], None),
  'C9':         ('C', [R,M3,P5,m7,n9],     [R,M3,m7,n9], None),
  'C9sus4':     ('C', [R,P4,P5,m7,n9],     [R,P4,m7,n9], None),
  'Bm7-5':      ('B',[R,m3,b5,m7],        [R,m3,b5,m7], None),
  'E7':         ('E',[R,M3,P5,m7],        [R,M3,m7], None),
  'E7(b9)':     ('E',[R,M3,P5,m7,b9],     [R,M3,m7,b9], None),
  'Em7':        ('E',[R,m3,P5,m7],        [R,m3,m7], None),
  'Em11':       ('E',[R,m3,P5,m7,n11],    [R,m3,m7,n11], None),
  # オンコード
  'Csus4/A':    ('C', [R,P4,P5],           [R,P4], 'A'),
  'C/Bb':       ('C', [R,M3,P5],           [R,M3], 'Bb'),
  'C/D':        ('C', [R,M3,P5],           [R,M3], 'D'),
  'F7/C':       ('F', [R,M3,P5,m7],        [R,M3,m7], 'C'),
  'Am7/D':      ('A', [R,m3,P5,m7],        [R,m3,m7], 'D'),
  'Em7/A':      ('E',[R,m3,P5,m7],        [R,m3,m7], 'A'),
  'E(b9)/G#':   ('E',[R,M3,P5,b9],        [R,M3,b9], 'G#'),
}

MAXF = 14

def fingers_needed(form):
    """form: 6要素(6弦->1弦), 'x' か int。押弦に必要な指の本数を見積る。
    セーハは「最低フレット」に限らず、どのフレットでも・どの範囲でも検討する
    （人差し指で低い音を押さえ、薬指で上を部分セーハする形なども拾うため）。
    押さえられない形は None。"""
    fr = [(i, v) for i, v in enumerate(form) if isinstance(v, int) and v > 0]
    if not fr:
        return 0
    frets = [v for _, v in fr]
    lo, hi = min(frets), max(frets)
    if hi - lo > 3:
        return None
    best = len(fr) if len(fr) <= 4 else None   # セーハ無しで押さえる場合
    sounding = [i for i, v in enumerate(form) if v != 'x']
    for f in sorted(set(frets)):
        # f フレットのセーハが覆う範囲 [i..5]（1弦側は必ず含む）
        for i in range(0, 6):
            span = [k for k in range(i, 6) if form[k] != 'x']
            if len(span) < 2:
                continue
            # セーハ範囲に開放弦・ミュート弦は作れない。f 未満の押弦も不可
            if any(form[k] == 'x' or form[k] == 0 or form[k] < f for k in range(i, 6)):
                continue
            if not any(form[k] == f for k in range(i, 6)):
                continue                      # そのフレットを実際に押さえていない
            cost = 1
            cost += sum(1 for k in range(i, 6) if form[k] > f)
            cost += sum(1 for k in sounding if k < i and form[k] > 0)
            if cost <= 4 and (best is None or cost < best):
                best = cost
    return best

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
