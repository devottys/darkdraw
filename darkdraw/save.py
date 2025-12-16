from pathlib import Path
from unittest import mock

from visidata import VisiData, colors, vd

from .drawing import Drawing, DrawingSheet
from .ansihtml import xterm256_to_rgb

from PIL import Image, ImageDraw, ImageFont

vd.option('darkdraw_font', '/usr/share/fonts/opentype/unifont/unifont.otf', 'path of font file for save_png')
vd.option('darkdraw_font_size', 16, 'font size for save_png')


@Drawing.api
def createPillowImage(dwg):
    im = Image.new("RGB", (640, 480), color=(0,0,0))

    draw = ImageDraw.Draw(im)
    font = None
    if Path(dwg.options.darkdraw_font).exists():
        font = ImageFont.truetype(dwg.options.darkdraw_font, dwg.options.darkdraw_font_size)
    else:
        vd.warning(f"{dwg.options.darkdraw_font} does not exist")

    vd.clearCaches()
    dwg._scr = mock.MagicMock(__bool__=mock.Mock(return_value=True),
                              getmaxyx=mock.Mock(return_value=(9999, 9999)))
    dwg.draw(dwg._scr)

    displayed = set()
    minX, minY = dwg.minXY
    maxX, maxY = dwg.maxXY
    for y in range(minY, maxY+1):
        for x in range(minX, maxX+1):
            rows = dwg._displayedRows.get((x,y), None)
            if not rows: continue
            r = rows[-1]
            k = str(r)
            if k in displayed: continue
            if not r.text: continue
            if x-r.x >= len(r.text): continue
            i = x-r.x
            s = r.text[i:]
            fg, bg, attrs = colors._split_colorstr(r.color)
            c = xterm256_to_rgb(fg)
            xy = ((r.x+i)*8, r.y*16)
            if bg:
                draw.rectangle((xy, (xy[0]+16, xy[1]+8)), fill=xterm256_to_rgb(bg))
            draw.text(xy, s, font=font, fill=c)
            if 'underline' in attrs:
                draw.line((xy, (xy[0]+16, xy[1])), fill=c)
                draw.line(((xy[0], xy[1]+8), (xy[0]+16, xy[1]+8)), fill=c)
            displayed.add(k)

    vd.status(' '.join(displayed))
    return im


@VisiData.api
def save_png(vd, p, *sheets):
    frames = []
    for vs in sheets:
        dwg = vs.drawing
        im = dwg.createPillowImage()

        if vs.frames:
            for i in range(vs.nFrames):
                dwg.cursorFrameIndex = i
                frames.append(dwg.createPillowImage())
        else:
            frames.append(dwg.createPillowImage())

    frames[0].save(str(p), append_images=frames[1:], save_all=True, duration=100, loop=0)


@VisiData.api
def save_gif(vd, p, *sheets):
    frames = []
    for vs in sheets:
        dwg = vs.drawing
        if vs.frames:
            for i in range(vs.nFrames):
                dwg.cursorFrameIndex = i
                frames.append(dwg.createPillowImage())
        else:
            frames.append(dwg.createPillowImage())

    frames[0].save(str(p), append_images=frames[1:], optimize=False, save_all=True, duration=100, loop=0)
