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

    frame_ids = {r['id'] for r in rows if r.get('type') == 'frame'}
    frame_rows = [r for r in rows if r.get('type') == 'frame']

    # Merge duplicate elements across frames
    merged = {}  # (x, y, text, color) -> set of frame ids
    for r in rows:
        if r.get('type') == 'frame':
            continue
        key = (r['x'], r['y'], r['text'], r['color'])
        merged.setdefault(key, set()).add(r['frame'])

    element_rows = []
    for (x, y, text, color), frames in merged.items():
        d = dict(x=x, y=y, text=text, color=color)
        if frames != frame_ids:
            d['frame'] = ' '.join(sorted(frames, key=int))
        element_rows.append(d)

    rows = frame_rows + element_rows

    rows = _combine_duplicate_frames(rows)

    ddwoutput = '\n'.join(json.dumps(r) for r in rows) + '\n'

    return DrawingSheet(p.name, source=Path(str(p.with_suffix('.ddw')), fptext=io.StringIO(ddwoutput))).drawing


def _combine_duplicate_frames(rows):
    'Replace later duplicate frames with another instance of the first matching frame.'
    def sig(fid):
        return frozenset(
            (r['x'], r['y'], r['text'], r['color'])
            for r in rows
            if not r.get('type') and fid in r.get('frame', '').split()
        )

    sigs = {}
    rename_map = {}  # dup_id -> first_id
    for r in rows:
        if r.get('type') != 'frame': continue
        s = sig(r['id'])
        if not s: continue
        if s in sigs:
            rename_map[r['id']] = sigs[s]
        else:
            sigs[s] = r['id']

    if not rename_map: return rows

    out = []
    dup_ids = set(rename_map)
    for r in rows:
        if r.get('type') == 'frame':
            if r['id'] in dup_ids:
                r = {**r, 'id': rename_map[r['id']]}
            out.append(r)
        else:
            ids = r.get('frame', '').split()
            if not ids:
                out.append(r)
                continue
            new_ids = [x for x in ids if x not in dup_ids]
            if not new_ids:
                continue
            if new_ids == ids:
                out.append(r)
            else:
                out.append({**r, 'frame': ' '.join(new_ids)})
    return out
