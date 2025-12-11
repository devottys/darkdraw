import json
import io
import gzip

from visidata import VisiData, Path
from . import DrawingSheet


durdraw_color16_fg_map = {
    0: 0, # black
    1: 0, # also black
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
    0: 0, # black
    1: 4, # blue
    2: 2, # green
    3: 6, # cyan
    4: 1, # red
    5: 5, # magenta
    6: 3, # yellow
    7: 7, # light grey
    8: 0, # also black
}

@VisiData.api
def open_dur(vd, p):
    dur = json.loads(gzip.open(str(p)).read())

    rows = []

    for f in dur['DurMovie']['frames']:
        n = f['frameNumber']
        lines = f['contents']
        colors = f['colorMap']
        if f['delay'] == 0: ### if delay is not specified, find duration based on animation framerate
            duration_ms = int(1000 // dur['DurMovie']['framerate'])
        else: ### if specified, convert to ms
            duration_ms = int(f['delay'] * 1000)

        d = dict(
            id=str(n),
            type='frame',
            duration_ms=duration_ms
        )
        rows.append(d)

        for y, line in enumerate(lines):
            for x, ch in enumerate(line):
                fg, bg = colors[x][y]
                if dur['DurMovie']['colorFormat'] == '16':
                    fg = durdraw_color16_fg_map[fg]
                    bg = durdraw_color16_bg_map[bg]
                # else use the standand 256 color mapping numbers as they are

                if ch == ' ' and bg == 0:
                    continue
                d = dict(x=x,
                         y=y,
                         text=ch,
                         color=f'{fg} on {bg}',
                         frame=str(n),
                        )
                rows.append(d)

    ddwoutput = '\n'.join(json.dumps(r) for r in rows) + '\n'

    return DrawingSheet(p.name, source=Path(str(p.with_suffix('.ddw')), fptext=io.StringIO(ddwoutput))).drawing
