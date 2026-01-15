from darkdraw import Drawing
from visidata import vd
from copy import copy

# semigraphical characters with 4 reflections
_UPPER_XY = '╭🭽🮠🮭🬀🬄🬔🬖🬥🬚🬆🬒🬕🬝▘▛🭈🭆🭂🭉🭃🭋🭅🭊🭁🭇🭄◢🮞🮟◣🭏🬼🭌🬿🭐🭀🭎🬾🭍🭑🬽▜▝🬬🬨🬡🬊🬩🬙🬢🬧🬉🬁🮬🮡🭾╮'
_LOWER_XY = '╰🭼🮢🮫🬏🬓🬣🬈🬳🬌🬱🬮🬲🬺▖▙🭣🭧🭓🭤🭔🭦🭖🭥🭒🭢🭕◥🮝🮜◤🭠🭗🭝🭚🭡🭛🭟🭙🭞🭜🭘▟▗🬻🬷🬯🬵🬍🬶🬅🬘🬦🬞🮪🮣🭿╯'

# semigraphical characters with only horizontal reflection
_HORIZ_CHARS = '🭮▏▎▍▌▋▊▉🮤🮨▏🭰🭱🭲🬛🬜▌🬴🬐🬟🬤╱▚🭪🮌🮍🭨▞╲🬗🬑🬠🬸▐🬪🬫🭳🭴🭵▕🮩🮥🮋🮊🮉▐🮈🮇▕🭬'

# semigraphical characters with only vertical reflection
_UPPER_VERT = '🬎▀🮑🮏🭫🭯🬭🬟▇▆▅▄▃▂▁🭻🭺🭹🬜▚🮧🮨╱'
_LOWER_VERT = '🬹▄🮒🮎🭩🭭🬂🬑🮆🮅🮄▀🮃🮂▔🭶🭷🭸🬪▞🮦🮩╲'


_HORIZ_MIRROR_MAP = {**{_UPPER_XY[i]: _UPPER_XY[-(i+1)] for i in range(len(_UPPER_XY))},
                     **{_LOWER_XY[i]: _LOWER_XY[-(i+1)] for i in range(len(_LOWER_XY))},
                     **{_HORIZ_CHARS[i]: _HORIZ_CHARS[-(i+1)] for i in range(len(_HORIZ_CHARS))}}

_VERT_MIRROR_MAP = {**{_UPPER_XY[i]: _LOWER_XY[i] for i in range(len(_UPPER_XY))},
                    **{_LOWER_XY[i]: _UPPER_XY[i] for i in range(len(_LOWER_XY))},
                    **{_UPPER_VERT[i]: _LOWER_VERT[i] for i in range(len(_UPPER_VERT))},
                    **{_LOWER_VERT[i]: _UPPER_VERT[i] for i in range(len(_LOWER_VERT))}}


@Drawing.api
def flip_horiz(sheet, box, rows):
    for r in rows:
        vd.addUndo(setattr, r, 'x', r.x)
        r.x = box.x2+box.x1-r.x-2


@Drawing.api
def flip_vert(sheet, box, rows):
    for r in rows:
        vd.addUndo(setattr, r, 'y', r.y)
        r.y = box.y2+box.y1-r.y-2


@Drawing.api
def mirror_horiz(sheet, rows):
    for r in rows:
        if r.text and r.text in _HORIZ_MIRROR_MAP:
            vd.addUndo(setattr, r, 'text', r.text)
            r.text = _HORIZ_MIRROR_MAP[r.text]


@Drawing.api
def mirror_vert(sheet, rows):
    for r in rows:
        if r.text and r.text in _VERT_MIRROR_MAP:
            vd.addUndo(setattr, r, 'text', r.text)
            r.text = _VERT_MIRROR_MAP[r.text]


Drawing.addCommand('', 'flip-cursor-horiz', 'flip_horiz(cursorBox, cursorRows)', 'Flip elements under cursor horizontally')
Drawing.addCommand('', 'flip-cursor-vert', 'flip_vert(cursorBox, cursorRows)', 'Flip elements under cursor vertically')
Drawing.addCommand('', 'mirror-cursor-horiz', 'mirror_horiz(cursorRows)', 'Mirror semigfx under cursor horizontally')
Drawing.addCommand('', 'mirror-cursor-vert', 'mirror_vert(cursorRows)', 'Mirror semigfx under cursor vertically')

Drawing.addCommand('', 'flip-selected-horiz', 'flip_horiz(selectedBox, sheet.selectedRows)', 'Flip selected elements horizontally')
Drawing.addCommand('', 'flip-selected-vert', 'flip_vert(selectedBox, sheet.selectedRows)', 'Flip selected elements vertically')
Drawing.addCommand('', 'mirror-selected-horiz', 'mirror_horiz(sheet.selectedRows)', 'Mirror semigfx for selected rows horizontally')
Drawing.addCommand('', 'mirror-selected-vert', 'mirror_vert(sheet.selectedRows)', 'Mirror semigfx for selected rows vertically')


vd.addMenuItems('''
    DarkDraw > Flip > cursor > horizontally > flip-cursor-horiz
    DarkDraw > Flip > cursor > vertically > flip-cursor-vert
    DarkDraw > Mirror > cursor > horizontally > mirror-cursor-horiz
    DarkDraw > Mirror > cursor > vertically > mirror-cursor-vert
    DarkDraw > Flip > selected > horizontally > flip-selected-horiz
    DarkDraw > Flip > selected > vertically > flip-selected-vert
    DarkDraw > Mirror > selected > horizontally > mirror-selected-horiz
    DarkDraw > Mirror > selected > vertically > mirror-selected-vert
''')
