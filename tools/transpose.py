# -*- coding: utf-8 -*-
"""貼付譜面（Play: F / Capo: 1）に合わせて、コード名を -2 半音へ付け替える。
表記の揺れは貼付譜面に合わせる（Eb->D#, Ab->G#）。"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))

FLATN  = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
PCMAP = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
         'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
# 貼付譜面の表記に合わせる上書き
SPELL = {'Eb': 'D#', 'Ab': 'G#'}

def shift_root(r, n):
    if r not in PCMAP:
        return r
    name = FLATN[(PCMAP[r] + n) % 12]
    return SPELL.get(name, name)

def transpose_name(name, n):
    if name == 'N.C.':
        return name
    out = []
    for part in str(name).split('/'):
        m = re.match(r'^([A-G][#b]?)(.*)$', part)
        out.append(shift_root(m.group(1), n) + m.group(2) if m else part)
    return '/'.join(out)

if __name__ == '__main__':
    N = -2
    path = os.path.join(HERE, 'measures.json')
    ms = json.load(io.open(path, encoding='utf-8'))
    seen = {}
    for mm in ms:
        for c in mm['chords']:
            old = c[0]
            c[0] = transpose_name(old, N)
            seen[old] = c[0]
    json.dump(ms, io.open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for k in sorted(seen):
        print('%-14s -> %s' % (k, seen[k]))
    print('---', len(seen), 'chords transposed;', len(ms), 'measures')
