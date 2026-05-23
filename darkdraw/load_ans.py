import json
import io

from visidata import VisiData, Path, vd
from . import DrawingSheet
from .ansi import AnsiParser, parse_sauce, resolve_encoding

# All .ans options (load and save)
vd.option('ans_columns', 80, 'width in characters for ANSI files')
vd.option('ans_icecolors', False, 'enable iCE colors (blinking -> bright backgrounds)')
vd.option('ans_encoding', 'cp437', 'character encoding: cp437/dos, iso8859-1/amiga, or utf-8')
vd.option('ans_vga_colors', False, 'convert SGR color codes to VGA palette when importing .ans files')
vd.option('ans_ignore_sauce', False, 'ignore SAUCE record for columns and iCE colors; use vd options instead')
vd.option('ans_256color', False, 'emit xterm 256-color SGR sequences when saving .ans files')
vd.option('ans_truecolor', False, 'emit 24-bit RGB SGR sequences (38;2;r;g;b) when saving .ans files')
vd.option('ans_sauce', True, 'write SAUCE record when saving .ans files')

@VisiData.api
def open_ans(vd, p):
    data = p.read_bytes()
    file_data, sauce = parse_sauce(data)

    enc = resolve_encoding(vd.options.ans_encoding)
    ignore_sauce = vd.options.ans_ignore_sauce

    # Infer encoding from SAUCE font name unless overridden
    if not ignore_sauce and sauce and sauce.t_info_s.startswith('Amiga'):
        enc = 'iso8859-1'

    if not ignore_sauce and sauce and sauce.t_info1:
        cols = sauce.t_info1
    else:
        cols = vd.options.ans_columns

    if not ignore_sauce and sauce:
        ice = bool(sauce.t_flags & 0x01)
    else:
        ice = vd.options.ans_icecolors

    vga = vd.options.ans_vga_colors

    parser = AnsiParser(columns=cols, icecolors=ice, encoding=enc, vga_colors=vga)
    chars = parser.parse(file_data)

    rows = []
    if sauce:
        spacer = {'id': '-', 'type': '-', 'text': '-', 'x': 0, 'y': 0, 'frame': '-'}
        rows.append(dict(spacer))
        rows.extend(sauce.sauce_to_rows())
        rows.append(dict(spacer))
    rows.extend([char.to_ddw_row(vga_colors=vga) for char in chars])

    ddwoutput = '\n'.join(json.dumps(r) for r in rows) + '\n'

    return DrawingSheet(
        p.name,
        source=Path(
            str(p.with_suffix('.ddw')),
            fptext=io.StringIO(ddwoutput)
        )
    ).drawing
