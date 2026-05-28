import gzip
import json

from visidata import VisiData, vd, AttrDict

from .ansi import parse_color_string, xterm256_to_ansi16

DUR_FORMAT_VERSION = 7
DEFAULT_FRAMERATE = 10
MAX_FRAMERATE = 50  # DurDraw caps playback at 50 fps

vd.option('dur_save_colormode', 'auto', 'force .dur export color mode: 16, 256, or auto')


# xterm color index -> DurDraw index. Inverses of the maps in load_dur.py.

_XTERM_TO_DUR16_FG = {
    0: 1, 16: 1,  # black
    1: 5, 2: 3, 3: 7, 4: 2, 5: 6, 6: 4, 7: 8,
    8: 9, 9: 13, 10: 11, 11: 15, 12: 10, 13: 14, 14: 12, 15: 16,
}

_XTERM_TO_DUR16_BG = {
    0: 0, 16: 0,  # black
    1: 4, 2: 2, 3: 6, 4: 1, 5: 5, 6: 3, 7: 7,
}

# 256 mode: first 16 entries reordered, indices 17-255 pass through unchanged.
_XTERM_TO_DUR256 = {
    0: 16, 1: 4, 2: 2, 3: 6, 4: 1, 5: 5, 6: 3, 7: 7,
    8: 8, 9: 12, 10: 10, 11: 14, 12: 9, 13: 13, 14: 11, 15: 15,
}


def _to_dur16_fg(c):
    if c in _XTERM_TO_DUR16_FG:
        return _XTERM_TO_DUR16_FG[c]
    return _XTERM_TO_DUR16_FG[xterm256_to_ansi16(c)]


def _to_dur16_bg(c):
    if c in _XTERM_TO_DUR16_BG:
        return _XTERM_TO_DUR16_BG[c]
    a = xterm256_to_ansi16(c)
    if a >= 8:  # 16-mode has only 8 background slots; drop brightness
        a -= 8
    return _XTERM_TO_DUR16_BG[a]


def _to_dur256(c):
    return _XTERM_TO_DUR256.get(c, c)


def _infer_colormode(sheet):
    'Return "256" if any element uses an extended foreground (xterm fg > 16), else "16".'
    for r, x, y, parents in sheet.iterdeep(sheet.rows):
        if not r.text:
            continue
        if parse_color_string(r.color or '').fg > 16:
            return '256'
    return '16'


def _resolve_colormode(sheet):
    opt = str(vd.options.dur_save_colormode or '').strip().lower()
    if opt == '16':
        return '16'
    if opt == '256':
        return '256'
    if opt in ('auto', 'infer', ''):
        return _infer_colormode(sheet)
    vd.fail(f'invalid dur_save_colormode: {opt!r} (expected 16, 256, or auto)')


@VisiData.api
def save_dur(vd, p, vs):
    'Save a DrawingSheet as a gzipped DurDraw .dur file.'
    dwg = vs.drawing
    sheet = dwg.source

    mode = _resolve_colormode(sheet)

    # Canvas bounds: union of all displayable elements (frames share one size).
    maxX = maxY = 0
    for r, x, y, parents in sheet.iterdeep(sheet.rows):
        if not r.text or x < 0 or y < 0:
            continue
        maxX = max(maxX, x + len(r.text) - 1)
        maxY = max(maxY, y)
    width, height = maxX + 1, maxY + 1

    frame_rows = sheet.frames
    if frame_rows:
        nonzero = [int(f.duration_ms or 0) for f in frame_rows if (f.duration_ms or 0) > 0]
        min_dur = min(nonzero) if nonzero else 0
        targets = list(enumerate(frame_rows, start=1))
    else:
        min_dur = 0
        targets = [(1, AttrDict())]

    framerate = min(1000 // min_dur, MAX_FRAMERATE) if min_dur > 0 else DEFAULT_FRAMERATE

    frames_out = []
    for fnum, f in targets:
        chars = [[' '] * width for _ in range(height)]
        fgs = [[7] * width for _ in range(height)]   # empty-cell default pair [7, 0]
        bgs = [[0] * width for _ in range(height)]

        for r, x, y, parents in sheet.iterdeep(sheet.rows):
            if not r.text:
                continue
            if (parents[0].frame or r.frame) and not dwg.inFrame(r, [f]):
                continue
            pc = parse_color_string(r.color or '')
            if mode == '256':
                fg, bg = _to_dur256(pc.fg), _to_dur256(pc.bg)
            else:
                fg, bg = _to_dur16_fg(pc.fg), _to_dur16_bg(pc.bg)
            for i, ch in enumerate(r.text):
                cx = x + i
                if 0 <= cx < width and 0 <= y < height:
                    chars[y][cx], fgs[y][cx], bgs[y][cx] = ch, fg, bg

        contents = [''.join(row) for row in chars]
        colorMap = [[[fgs[y][x], bgs[y][x]] for y in range(height)] for x in range(width)]

        dur_ms = int(f.duration_ms or 0)
        delay = dur_ms / 1000 if (min_dur > 0 and dur_ms and dur_ms != min_dur) else 0

        frames_out.append(dict(
            frameNumber=fnum,
            delay=delay,
            contents=contents,
            colorMap=colorMap,
        ))

    name = artist = ''
    for r in sheet.rows:
        if (r.get('frame') or '') == 'SAUCE_record':
            label = r.get('type') or ''
            if label == 'Title':
                name = (r.get('text') or '').strip()
            elif label == 'Author':
                artist = (r.get('text') or '').strip()

    movie = dict(DurMovie=dict(
        formatVersion=DUR_FORMAT_VERSION,
        colorFormat=mode,
        preferredFont='fixed',
        encoding='utf-8',
        name=name,
        artist=artist,
        framerate=float(framerate),
        sizeX=width,
        sizeY=height,
        extra=None,
        frames=frames_out,
    ))

    # DurDraw detects a JSON .dur by an exact byte-prefix sniff ('{\n  "DurMovie')
    # before it ever calls json.load, so indent=2 is required, not cosmetic.
    with gzip.open(str(p), 'wt', encoding='utf-8') as fp:
        json.dump(movie, fp, indent=2)
