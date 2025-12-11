import collections
import random
import json

from visidata import vd, VisiData, dispwidth

from darkdraw import Drawing

vd.option('keymap', 'keymap.jsonl', 'JSONL keymap filename to load for DarkDraw typing mode')

Drawing.init('typing_mode_map', dict)

@VisiData.api
def typing_mode(vd, scr):
    ddw = vd.activeSheet
    if not ddw.typing_mode_map:
        try:
            ddw.keymap_layers = []
            ddw.load_keymap(ddw.options.keymap)
        except Exception as e:
            vd.exceptionCaught(e)

    oldmode = ddw.paste_mode
    try:
        ddw.paste_mode = ''
        ddw.run_typing_mode(scr)
    finally:
        ddw.paste_mode = oldmode


@Drawing.api
def load_keymap(ddw, fn):
    keymap_layers = dict(random=1)
    with open(fn) as fp:
        ddw.typing_mode_map = collections.defaultdict(dict)
        for line in fp:
            d = json.loads(line)
            keych = d.pop('keypress')
            for keymap_layer, v in d.items():
                ddw.typing_mode_map[keych][keymap_layer] = v
                keymap_layers[keymap_layer] = 2
    ddw.keymap_layers = list(keymap_layers.keys())


def rotate(L:list, n:int):
    return L[n:] + L[:n]

@Drawing.api
def run_typing_mode(ddw, scr):
    cur_edits = {}
    last_dispwidth = 0

    while True:
        ddw.paste_mode = ddw.keymap_layers[0] + ' layer'
        vd.drawSheet(scr, ddw)
        x, y = ddw.cursorBox.x1, ddw.cursorBox.y1

        if scr: scr.move(y, x)
        ch = vd.getkeystroke(scr)
        if ch == '':     continue
        elif ch == '^Q':  return
        elif ch == '^[':  return
        elif ch == '^C':  return
        elif ch == '^J':        y += 1; x = 0
        elif ch == 'KEY_UP':    y -= 1
        elif ch == 'KEY_DOWN':  y += 1
        elif ch == 'KEY_LEFT':  x -= 1
        elif ch == 'KEY_RIGHT': x += 1
        elif ch == 'KEY_BACKSPACE':
            x -= last_dispwidth
            if (x,y) in cur_edits:
                ddw.rows.remove(cur_edits[(x,y)])
                del cur_edits[(x,y)]

        elif ch == '^P':
            ddw.keymap_layers = rotate(ddw.keymap_layers, -1)
        elif ch == '^N':
            ddw.keymap_layers = rotate(ddw.keymap_layers, +1)

        elif len(ch) == 1:
            poss = ddw.typing_mode_map.get(ch, {'straight': ch})
            layer = ddw.keymap_layers[0]
            if layer == 'random':
                s = random.choice(list(poss.values()))
            else:
                s = poss.get(layer, ch)
            if (x,y) in cur_edits:
                ddw.rows.remove(cur_edits[(x,y)])
            cur_edits[(x,y)] = ddw.add_text(s, x, y, vd.default_color)
            last_dispwidth = dispwidth(s)
            x += last_dispwidth
        else:
            vd.status(f'unknown keypress {ch}')

        ddw.cursorBox.x1 = max(0, x)
        ddw.cursorBox.y1 = max(0, y)


Drawing.addCommand('Shift+N', 'typing-mode', 'vd.typing_mode(_scr)', 'enter raw typing mode')
Drawing.addCommand('zShift+N', 'load-keymap', 'load_keymap(inputFilename("keymap to load: ", value=options.keymap))', 'load different keymap for typing mode')
