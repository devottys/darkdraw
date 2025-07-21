#!python3

'''
Usage:
    $0 <drawing.dur>

Convert <drawing.dur> to <drawing.dur>.ddw.
'''

import sys
import json
import gzip

durdraw_color16_fg_map = {
        0: -1, #??
    1: 0, # black
    2: 4, # blue
    3: 2, # green
    4: 6, # cyan
    5: 1, # red
    6: 5, # magenta
    7: 3, # yellow
    8: 7, # light grey
    9: 8, # dark grey
    10: 12, # bright blue
    11: 10, # bright green
    12: 14, # bright cyan
    13: 9, # bright red
    14: 13, # bright magenta
    15: 11, # bright yellow
    16: 15, # white
}

durdraw_color16_bg_map = {
        0: -1, #??
    1: 4, # blue
    2: 2, # green
    3: 6, # cyan
    4: 1, # red
    5: 5, # magenta
    6: 3, # yellow
    7: 7, # light grey
    8: 0, # black
}

def convert_dur_to_ddw(infn, outfp):
    dur = json.loads(gzip.open(infn).read())

    for f in dur['DurMovie']['frames']:
        n = f['frameNumber']
        lines = f['contents']
        colors = f['colorMap']

        d = dict(
            id=str(n),
            type='frame',
            duration_ms=f['delay']
        )
        print(json.dumps(d), file=outfp)

        for y, line in enumerate(lines):
            for x, ch in enumerate(line):
                fg, bg = colors[x][y]
                fg = durdraw_color16_fg_map[fg]
                bg = durdraw_color16_bg_map[bg]
                if ch == ' ' and bg == 0:
                    continue
                d = dict(x=x,
                         y=y,
                         text=ch,
                         color=f'{fg} on {bg}',
                         frame=str(n),
                        )
                print(json.dumps(d), file=outfp)


for fn in sys.argv[1:]:
    outfn = fn + '.ddw'
    with open(outfn, mode='w') as outfp:
        convert_dur_to_ddw(fn, outfp)
