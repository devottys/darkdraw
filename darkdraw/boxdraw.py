from darkdraw import Drawing
from visidata import vd

### RECTANGLE TOOL #########################################################
@Drawing.api
def set_box_chars(sheet):
    if not hasattr(vd, 'box_chars'):
        vd.box_chars = ['─', '│', '┌', '┐', '└', '┘']
    
    current = ' '.join(vd.box_chars)
    result = vd.input("box chars (horiz vert tl tr bl br): ", value=current)
    
    if result:
        chars = result.split()
        if len(chars) == 6:
            vd.box_chars = chars
            vd.status(f"box chars set: {' '.join(vd.box_chars)}")
        else:
            vd.fail("need exactly 6 characters separated by spaces")


@Drawing.api
def box_cursor(sheet):
    if not hasattr(vd, 'box_chars'):
        vd.box_chars = ['─', '│', '┌', '┐', '└', '┘']
    
    horiz, vert, tl, tr, bl, br = vd.box_chars
    box = sheet.cursorBox
    
    # Corners
    sheet.add_text(tl, box.x1, box.y1, vd.default_color)
    sheet.add_text(tr, box.x2-2, box.y1, vd.default_color)
    sheet.add_text(bl, box.x1, box.y2-2, vd.default_color)
    sheet.add_text(br, box.x2-2, box.y2-2, vd.default_color)
    
    # Horizontal edges
    for x in range(box.x1 + 1, box.x2 - 2):
        sheet.add_text(horiz, x, box.y1, vd.default_color)
        sheet.add_text(horiz, x, box.y2-2, vd.default_color)
    
    # Vertical edges
    for y in range(box.y1 + 1, box.y2 - 2):
        sheet.add_text(vert, box.x1, y, vd.default_color)
        sheet.add_text(vert, box.x2-2, y, vd.default_color)

Drawing.addCommand('', 'set-box-chars', 'sheet.set_box_chars()', 'set characters for drawing boxes (format: horiz vert tl tr bl br)')
Drawing.addCommand('', 'box-cursor', 'sheet.box_cursor()', 'draw a box to fill the inner edge of the cursor')

