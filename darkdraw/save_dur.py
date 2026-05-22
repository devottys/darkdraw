import json
import gzip

from visidata import VisiData, vd, dispwidth

from .load_dur import durdraw_color16_fg_map, durdraw_color16_bg_map


vd.option('dur_color_format', '256', 'color format for .dur output: "16" or "256"')


_KNOWN_ATTRS = {'bold', 'dim', 'italic', 'underline', 'blink', 'reverse', 'standout', 'strikethrough'}


def _invert_map(m):
    out = {}
    for k, v in m.items():
        out.setdefault(v, k)
    return out


_inv_fg16 = _invert_map(durdraw_color16_fg_map)
_inv_bg16 = _invert_map(durdraw_color16_bg_map)


def _parse_color(s, dropped_attrs):
    fg, bg = 7, 0
    if not s:
        return fg, bg
    parts = s.split(' on ')
    fg_toks = parts[0].split()
    bg_toks = parts[1].split() if len(parts) > 1 else []

    def _take_int(toks):
        n = None
        for t in toks:
            try:
                n = int(t)
                break
            except ValueError:
                if t in _KNOWN_ATTRS:
                    dropped_attrs.add(t)
        return n

    f = _take_int(fg_toks)
    b = _take_int(bg_toks)
    if f is not None: fg = f
    if b is not None: bg = b
    return fg, bg


def _to_dur_color(fg, bg, fmt, lossy_colors):
    if fmt == '16':
        if fg in _inv_fg16:
            dfg = _inv_fg16[fg]
        else:
            lossy_colors.add(fg)
            dfg = 1
        if bg in _inv_bg16:
            dbg = _inv_bg16[bg]
        else:
            lossy_colors.add(bg)
            dbg = 0
        return dfg, dbg
    return fg, bg


def _resolve_sheet(vs):
    'Return DrawingSheet whether vs is Drawing or DrawingSheet.'
    rows = getattr(vs, 'rows', None)
    src = getattr(vs, 'source', None)
    if rows is not None and any((getattr(r, 'type', '') or '') == 'frame' for r in rows):
        return vs
    if src is not None and hasattr(src, 'rows'):
        return src
    return vs


@VisiData.api
def save_dur(vd, p, vs):
    src = _resolve_sheet(vs)
    fmt = vd.options.dur_color_format
    if fmt not in ('16', '256'):
        vd.fail(f'dur_color_format must be "16" or "256" (got {fmt!r})')

    rows = list(src.rows)

    # SAUCE → name / artist
    name = ''
    artist = ''
    for r in rows:
        if (r.get('frame') or '') != 'SAUCE_record':
            continue
        if r.get('type') == 'Title':
            name = (r.get('text') or '').strip()
        elif r.get('type') == 'Author':
            artist = (r.get('text') or '').strip()

    frames = [r for r in rows if (r.get('type') or '') == 'frame']
    synthesized_frame = False
    if not frames:
        from visidata import AttrDict
        frames = [AttrDict(id='1', duration_ms=0)]
        synthesized_frame = True

    disabled_tags = getattr(vs, 'disabled_tags', set()) or set()

    # Flatten elements via iterdeep (resolves refs/groups). Skip frames + disabled-tagged.
    elements = []
    for r, x, y, parents in src.iterdeep(rows):
        typ = (r.get('type') or '')
        if typ:  # group/ref/sauce-style rows
            continue
        if (r.get('frame') or '') == 'SAUCE_record':
            continue
        text = r.get('text') or ''
        if not text:
            continue
        tags = (r.get('tags') or '').split()
        if disabled_tags and any(t in disabled_tags for t in tags):
            continue
        elements.append((r, x, y, text))

    if not elements:
        vd.fail('no elements to save')

    cols = max(x + dispwidth(t) for _, x, _, t in elements)
    lines = max(y + 1 for _, _, y, _ in elements)

    # Framerate from shortest frame
    durs = [f.duration_ms for f in frames if f.duration_ms]
    if durs:
        min_dur = min(durs)
        framerate = 1000.0 / min_dur
    else:
        min_dur = None
        framerate = 10.0

    dropped_attrs = set()
    lossy_colors = set()

    dur_frames = []
    for n, f in enumerate(frames, start=1):
        contents = [[' '] * cols for _ in range(lines)]
        colormap = [[[1, 0] for _ in range(lines)] for _ in range(cols)]

        fid = f.get('id') if hasattr(f, 'get') else getattr(f, 'id', None)
        for r, x, y, text in elements:
            rframe = r.get('frame') or ''
            if not synthesized_frame and rframe and (fid is None or str(fid) not in rframe.split()):
                continue
            fg, bg = _parse_color(r.get('color') or '', dropped_attrs)
            dfg, dbg = _to_dur_color(fg, bg, fmt, lossy_colors)
            w = dispwidth(text) or 1
            if 0 <= y < lines:
                for i, ch in enumerate(text):
                    cx = x + i
                    if 0 <= cx < cols:
                        contents[y][cx] = ch
                for i in range(w):
                    cx = x + i
                    if 0 <= cx < cols:
                        colormap[cx][y] = [dfg, dbg]

        dur_dur = f.get('duration_ms') if hasattr(f, 'get') else getattr(f, 'duration_ms', 0)
        if min_dur and dur_dur and dur_dur != min_dur:
            delay = dur_dur / 1000.0
        else:
            delay = 0

        dur_frames.append({
            'frameNumber': n,
            'delay': delay,
            'contents': [''.join(line) for line in contents],
            'colorMap': colormap,
        })

    movie = {
        'DurMovie': {
            'formatVersion': 7,
            'colorFormat': fmt,
            'preferredFont': 'fixed',
            'encoding': 'utf-8',
            'name': name,
            'artist': artist,
            'framerate': framerate,
            'sizeX': cols,
            'sizeY': lines,
            'extra': None,
            'frames': dur_frames,
        }
    }

    if dropped_attrs:
        vd.warning(f'.dur drop unsupported attrs: {", ".join(sorted(dropped_attrs))}')
    if lossy_colors:
        vd.warning(f'.dur 16-color mode lossy for colors: {sorted(lossy_colors)}')

    with gzip.open(str(p), 'wt', encoding='utf-8') as fp:
        json.dump(movie, fp, indent=2)
