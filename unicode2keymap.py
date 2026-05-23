#!/usr/bin/env python3

import unicodedata
import collections
import re
import json

keymap = collections.defaultdict(dict)

for i in range(32, 0x10000):
    ch = chr(i)
    if unicodedata.category(ch)[0] in 'CM':
        continue

    name = unicodedata.name(ch)

    if 'LATIN' not in name:
        continue

    m = re.match(r'(.*) LETTER (.)\b(.*)', name)
    if m:
        layer, letter, suffix = m.groups()
        layername = f'{layer}{suffix}'.replace('LATIN', '')
        layername = layername.replace('  ', ' ')
        keymap[letter.lower()][layername] = ch


for letter, layers in keymap.items():
    print(json.dumps(dict(keypress=letter, **layers)))
