from visidata import VisiData, vd

from .ansi import (
    parse_color_string, DdwChar, render_ansi,
    build_sauce_block, build_comment_block, rebuild_sauce,
    resolve_encoding,
)

@VisiData.api
def save_ans(vd, p, vs):
    """Save a DrawingSheet as an ANSI .ans file, exporting only base-frame rows."""
    chars = []
    sauce_fields = {}

    for row in vs.rows:
        frame = row.get('frame', '') or ''
        typ = row.get('type', '') or ''
        text = row.get('text', '') or ''

        if not text:
            continue

        # Collect SAUCE metadata
        if frame == 'SAUCE_record':
            sauce_fields[typ] = text
            continue

        # Skip non-base-frame rows (animation frames, frame markers)
        if frame or typ:
            continue

        chars.append(DdwChar(
            x=int(row.get('x', 0) or 0),
            y=int(row.get('y', 0) or 0),
            text=text,
            color=parse_color_string(row.get('color', '') or ''),
        ))

    if not chars:
        vd.fail('Drawing is animation; cannot export as ANSI.')

    sauce = rebuild_sauce(sauce_fields) if sauce_fields else None

    cols     = vd.options.ans_columns
    ice      = vd.options.ans_icecolors
    use_256  = vd.options.ans_256color
    use_true = vd.options.ans_truecolor
    do_sauce = vd.options.ans_sauce
    enc      = resolve_encoding(vd.options.ans_encoding)

    # Infer output params from SAUCE unless user overrides
    if sauce and not vd.options.ans_ignore_sauce:
        if sauce.t_info1:
            cols = sauce.t_info1
        ice = bool(sauce.t_flags & 0x01)
        if sauce.t_info_s.startswith('Amiga'):
            enc = 'iso8859-1'

    ansi_bytes = render_ansi(chars, columns=cols,
                             use_256color=use_256, icecolors=ice,
                             use_truecolor=use_true, encoding=enc)

    with p.open_bytes(mode='wb') as f:
        f.write(ansi_bytes)
        f.write(bytes([26]))

        if do_sauce and sauce:
            file_size     = len(ansi_bytes)
            comment_block = build_comment_block(sauce.comments)
            sauce_block   = build_sauce_block(
                sauce, file_size,
                columns=sauce.t_info1 or cols,
                rows=sauce.t_info2 or 0,
            )
            f.write(comment_block)
            f.write(sauce_block)
