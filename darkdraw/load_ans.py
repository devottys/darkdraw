import io
import re
import json
from visidata import VisiData, Path
from . import DrawingSheet

@VisiData.api
def open_ans(vd, p):
    with open(str(p), 'rb') as f:
        data = f.read()
    
    # Try UTF-8 first, fall back to CP437
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        text = data.decode('cp437', errors='replace')
    
    rows = []
    x, y = 0, 0
    fg, bg = 7, 0  # default white on black
    bold = False
    dim = False
    italic = False
    underline = False
    blink = False
    reverse = False
    
    # Parse ANSI escape sequences: ESC [ <params> m
    ansi_pattern = re.compile(r'\x1b\[([0-9;]*)m')
    pos = 0
    
    while pos < len(text):
        match = ansi_pattern.match(text, pos)
        if match:
            params = match.group(1)
            param_list = [int(p) if p else 0 for p in params.split(';')] if params else [0]
            
            i = 0
            while i < len(param_list):
                param = param_list[i]
                
                if param == 0:  # reset
                    fg, bg = 7, 0
                    bold = dim = italic = underline = blink = reverse = False
                elif param == 1:  # bold
                    bold = True
                elif param == 2:  # dim
                    dim = True
                elif param == 3:  # italic
                    italic = True
                elif param == 4:  # underline
                    underline = True
                elif param == 5 or param == 6:  # blink (slow or rapid)
                    blink = True
                elif param == 7:  # reverse video
                    reverse = True
                elif param == 22:  # normal intensity (not bold or dim)
                    bold = dim = False
                elif param == 23:  # not italic
                    italic = False
                elif param == 24:  # not underlined
                    underline = False
                elif param == 25:  # not blinking
                    blink = False
                elif param == 27:  # not reversed
                    reverse = False
                elif 30 <= param <= 37:  # standard fg colors
                    fg = param - 30
                elif param == 38:  # extended fg color
                    if i + 1 < len(param_list) and param_list[i + 1] == 5:  # 256-color
                        if i + 2 < len(param_list):
                            fg = param_list[i + 2]
                            i += 2
                    elif i + 1 < len(param_list) and param_list[i + 1] == 2:  # RGB (skip)
                        i += 4 if i + 4 < len(param_list) else len(param_list) - i - 1
                elif param == 39:  # default fg
                    fg = 7
                elif 40 <= param <= 47:  # standard bg colors
                    bg = param - 40
                elif param == 48:  # extended bg color
                    if i + 1 < len(param_list) and param_list[i + 1] == 5:  # 256-color
                        if i + 2 < len(param_list):
                            bg = param_list[i + 2]
                            i += 2
                    elif i + 1 < len(param_list) and param_list[i + 1] == 2:  # RGB (skip)
                        i += 4 if i + 4 < len(param_list) else len(param_list) - i - 1
                elif param == 49:  # default bg
                    bg = 0
                elif 90 <= param <= 97:  # bright fg colors
                    fg = param - 90 + 8
                elif 100 <= param <= 107:  # bright bg colors
                    bg = param - 100 + 8
                
                i += 1
            
            pos = match.end()
        else:
            ch = text[pos]
            if ch == '\r':
                x = 0
            elif ch == '\n':
                x = 0
                y += 1
            elif ch == '\x1a':  # EOF marker, stop processing
                break
            else:
                if ch != ' ' or bg != 0:
                    # Build style string
                    styles = []
                    if bold:
                        styles.append('bold')
                    if dim:
                        styles.append('dim')
                    if italic:
                        styles.append('italic')
                    if underline:
                        styles.append('underline')
                    if blink:
                        styles.append('blink')
                    if reverse:
                        styles.append('reverse')
                    
                    style_str = ' '.join(styles)
                    color_str = f'{fg} on {bg}'
                    if style_str:
                        color_str = f'{color_str} {style_str}'
                    
                    rows.append(dict(
                        x=x,
                        y=y,
                        text=ch,
                        color=color_str,
                    ))
                x += 1
            pos += 1
    
    ddwoutput = '\n'.join(json.dumps(r) for r in rows) + '\n'
    
    return DrawingSheet(p.name, source=Path(str(p.with_suffix('.ddw')), fptext=io.StringIO(ddwoutput))).drawing
