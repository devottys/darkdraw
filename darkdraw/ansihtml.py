from unittest import mock
from pkg_resources import resource_filename
from visidata import AttrDict, VisiData, colors, vd, dispwidth
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
    return ' '.join('%s="%s"' % (k,v) for k, v in d.items() if v)


def colorstr_to_style(color):
    fg, bg, attrs = split_colorstr(color)

    style = ''
    classes = []
    if 'underline' in attrs:
#        style += f'text-decoration: underline; '
        classes.append('underline')
    if 'bold' in attrs:
#        style += f'font-weight: bold; '
        classes.append('bold')
    if 'reverse' in attrs:
        bg, fg = fg, bg
    if bg:
        bg = termcolor_to_css_color(bg)
        style += f'background-color: {bg}; '
    if fg:
        fg = termcolor_to_css_color(fg)
        style += f'color: {fg}; '
    ret = dict(style=style)
    if classes:
        ret['class'] = ' '.join(classes)
    return ret

def iterline(dwg, y):
    leftover = 0
    for x in range(dwg.minX, dwg.maxX+1):
#        if leftover:
#            leftover -= 1
#            continue

        rows = dwg._displayedRows.get((x,y), None)
        if not rows:
            yield x, ' ', AttrDict()
        else:
            for i in range(len(rows)):
                r = rows[-i-1]
                if dispwidth(r.text) > x-r.x:
                    break
            if len(r.text) > x-r.x:
                ch = r.text[x-r.x]
                yield x, ch, r
                leftover = dispwidth(ch) - 1
            else:
                yield x, ' ', AttrDict()


def matches(a, b, attrs):
    return all(a.get(attr) == b.get(attr) for attr in attrs)


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
            line = ''
            text = ''
            lastrow = AttrDict()
            for x, ch, r in iterline(dwg, y):
                divch = f'<div>{ch}</div>'
                if matches(r, lastrow, 'color id class href title'.split()):
                    text += divch
                    continue

                if text:
                    kwargs = colorstr_to_style(lastrow.color)

                    spanattrstr = htmlattrstr(lastrow, 'id class'.split(), **kwargs)
                    span = f'<span {spanattrstr}>{text}</span>'
                    if lastrow.href:
                        linkattrstr = htmlattrstr(lastrow, 'href title'.split())
                        span = f'<a {linkattrstr}>{span}</a>'

                    line += span

                text = divch
                lastrow = r

            body += f'<div>{line}</div>\n'
        body += '</pre>\n'

    try:
        tmpl = open(vs.options.darkdraw_html_tmpl).read()
        out = tmpl.replace('$body$', body)
    except FileNotFoundError as e:
        vd.exceptionCaught(e)
        out = body

    with p.open_text(mode='w') as fp:
        fp.write(out)
