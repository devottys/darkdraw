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
def mirror_horiz(sheet, box):
    for r in sheet.iterbox(box):
        # Flip position
        oldx = copy(r.x)
        r.x = box.x2 + box.x1 - r.x - 2
        vd.addUndo(setattr, r, 'x', oldx)
        
        # Mirror character if mapping exists
        if r.text and r.text in _HORIZ_MIRROR_MAP:
            oldtext = r.text
            r.text = _HORIZ_MIRROR_MAP[r.text]
            vd.addUndo(setattr, r, 'text', oldtext)


@Drawing.api
def mirror_vert(sheet, box):
    for r in sheet.iterbox(box):
        # Flip position
        oldy = r.y
        r.y = box.y2 + box.y1 - r.y - 2
        vd.addUndo(setattr, r, 'y', oldy)
        
        # Mirror character if mapping exists
        if r.text and r.text in _VERT_MIRROR_MAP:
            oldtext = r.text
            r.text = _VERT_MIRROR_MAP[r.text]
            vd.addUndo(setattr, r, 'text', oldtext)


Drawing.addCommand('', 'mirror-x-cursor', 'mirror_horiz(cursorBox)', 
                   'Mirror elements under cursor horizontally (also use mirror semigfx)')
Drawing.addCommand('', 'mirror-y-cursor', 'mirror_vert(cursorBox)', 
                   'Mirror elements under cursor vertically (also use mirror semigfx)')
