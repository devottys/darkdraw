from unittest import mock
from pkg_resources import resource_filename
from visidata import AttrDict, VisiData, colors, vd
import curses

from .drawing import Drawing, DrawingSheet

vd.option('darkdraw_html_tmpl', resource_filename(__name__, 'ansi.html'), '')


def split_colorstr(colorstr):
        'Return (fgstr, bgstr, attrlist) parsed from colorstr.'
        fgbgattrs = ['', '', []]  # fgstr, bgstr, attrlist
        if not colorstr:
            return fgbgattrs
        colorstr = str(colorstr)

        i = 0  # fg by default
        for x in colorstr.split():
            if x == 'fg':
                i = 0
                continue
            elif x in ['on', 'bg']:
                i = 1
                continue

            if hasattr(curses, 'A_' + x.upper()):
                fgbgattrs[2].append(x)
            else:
                if not fgbgattrs[i]:  # keep first known color
                    fgbgattrs[i] = x

        return fgbgattrs



def termcolor_to_rgb(n):
    if not n:
        return (255,255,255)
    colordict = dict(
            black=(0,0,0),
            blue=(114,159,207),
            green=(78,154,6),
            red=(204,0,0),
            cyan=(6,152,154),
            magenta=(255,0,255),
            brown=(196,160, 0),
            white=(211,215,207),
            gray=(85,87,83),
            lightblue=(50,175,255),
            lightgreen=(138,226,52),
            lightaqua=(52,226,226),
            lightred=(239,41,41),
            lightpurple=(173,127,168),
            lightyellow=(252,233,79),
            brightwhite=(255,255,255),
    )
    if n in colordict:
        return colordict.get(n)
    n = int(n)
    if 0 <= n < 16:
        return list(colordict.values())[n]
    if 16 <= n < 232:
        n -= 16
        r,g,b = n//36,(n%36)//6,n%6
        ints = [0x00, 0x66, 0x88,0xbb,0xdd,0xff]
        return ints[r],ints[g],ints[b]
    else:
        n=list(range(8,255,10))[n-232]
        return n,n,n


def termcolor_to_css_color(n):
    if not n.isdigit():
        return n
    r,g,b = termcolor_to_rgb(n)
    return '#%02x%02x%02x' % (r,g,b)

def htmlattrstr(r, attrnames, **kwargs):
    d = AttrDict(kwargs)
    for a in attrnames:
        if a in r:
            d[a] = r[a]
    return ' '.join('%s="%s"' % (k,v) for k, v in d.items())


@VisiData.api
def save_ansihtml(vd, p, *sheets):
    for vs in sheets:
        if isinstance(vs, DrawingSheet):
            dwg = Drawing('', source=vs)
        elif isinstance(vs, Drawing):
            dwg = vs
        else:
            vd.fail(f'{vs.name} not a drawing')

        dwg._scr = mock.MagicMock(__bool__=mock.Mock(return_value=True),
                                  getmaxyx=mock.Mock(return_value=(9999, 9999)))
        dwg.reload()
        dwg.draw(dwg._scr)
        body = '''<pre>'''
        for y in range(dwg.minY, dwg.maxY+1):
            for x in range(dwg.minX, dwg.maxX+1):
                rows = dwg._displayedRows.get((x,y), None)
                if not rows:
                    body += '<span> </span>'
                else:
                    r = rows[-1]
                    ch = r.text[x-r.x]
                    fg, bg, attrs = split_colorstr(r.color)

                    style = ''
                    if 'underline' in attrs:
                        style += f'text-decoration: underline; '
                    if 'bold' in attrs:
                        style += f'font-weight: bold; '
                    if 'reverse' in attrs:
                        bg, fg = fg, bg
                    if bg:
                        bg = termcolor_to_css_color(bg)
                        style += f'background-color: {bg}; '
                    if fg:
                        fg = termcolor_to_css_color(fg)
                        style += f'color: {fg}; '

                    spanattrstr = htmlattrstr(r, 'id class'.split(), style=style)
                    span = f'<span {spanattrstr}>{ch}</span>'
                    if r.href:
                        linkattrstr = htmlattrstr(r, 'href title'.split())
                        body += f'<a {linkattrstr}>{span}</a>'
                    else:
                        body += span

            body += '\n'
        body += '</pre>\n'

    try:
        tmpl = open(vs.options.darkdraw_html_tmpl).read()
        out = tmpl.replace('<body>', '<body>'+body)
    except FileNotFoundError:
        out = body

    with p.open_text(mode='w') as fp:
        fp.write(out)
