from visidata import VisiData, colors
from .drawing import Drawing, DrawingSheet
from .ansihtml import termcolor_to_css_color
from unittest import mock

from PIL import Image, ImageDraw, ImageFont

@VisiData.api
def save_png(vd, p, *sheets):
    im = Image.new("RGB", (640, 480), color=0)

    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype("/usr/share/fonts/truetype/unifont/unifont.ttf", 16)

    for vs in sheets:
        if isinstance(vs, DrawingSheet):
            dwg = Drawing('', source=vs)
        elif isinstance(vs, Drawing):
            dwg = vs
        else:
            vd.fail(f'{vs.name} not a drawing')

        dwg._scr = mock.MagicMock(__bool__=mock.Mock(return_value=True),
                                  getmaxyx=mock.Mock(return_value=(9999, 9999)))
        dwg.draw(dwg._scr)

        displayed = set()
        for y in range(dwg.minY, dwg.maxY+1):
            for x in range(dwg.minX, dwg.maxX+1):
                rows = dwg._displayedRows.get((x,y), None)
                if not rows: continue
                r = rows[-1]
                k = str(r)
                if k in displayed: continue
                if not r.text: continue
                if x-r.x >= len(r.text): continue
                i = x-r.x
                s = r.text[i:]
                fg, bg, attrs = colors.split_colorstr(r.color)
                if r.color: vd.status(r.color)
                if fg: vd.status(fg)
                draw.text(((r.x+i)*8, r.y*16), s, font=font, fill=termcolor_to_css_color(fg) or None, anchor='mm')
                displayed.add(k)

    im.save(str(p))
