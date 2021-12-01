from visidata import CharBox, vd
import itertools
from darkdraw import Drawing

@Drawing.api
def stamp_circle(sheet, box):
    import math
    # attributes that i have:
    # box.x1, box.x2, box.y1, box.y2, box.h, box.w

    # x = cen_x + (r * cosine(theta))
    # y = cen_y + (r * sine(theta))
    xr = (box.w-1)/2
    yr = (box.h-1)/2
    x = (2*box.x1 + box.w)/2
    y = (2*box.y1 + box.h)/2

    coords = set()
    for theta in range(0, 361):
        # i need radians
        theta = math.radians(theta)
        coords.add((int(x+(xr*math.cos(theta))), int(y+(yr*math.sin(theta)))))

    itchars = itertools.cycle([(r.text, r.color) for r in vd.memory.cliprows or []] or [('*', '')])
    for coord in coords:
        ch, color = next(itchars)
        sheet.place_text(ch, CharBox(x1=coord[0], y1=coord[1]), go_forward=False)


Drawing.addCommand('', 'stamp-circle', 'sheet.stamp_circle(cursorBox); # sheet.go_forward(cursorBox.w, 0)')

