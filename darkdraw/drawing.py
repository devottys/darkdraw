from unittest import mock
from collections import defaultdict
import itertools
import functools
from random import choice
import time
import unicodedata
from copy import copy, deepcopy
from visidata import *
from visidata import dispwidth, CharBox, boundingBox, asyncthread


vd.allPrefixes += list('01')
vd.option('pen_down', False, 'is pen down')
vd.option('disp_guide_xy', '', 'x y position of onscreen guides')
vd.option('autosave_interval_s', 0, 'seconds between autosave')
vd.option('autosave_path', 'autosave', 'path to put autosave files')
vd.option('ddw_add_baseframe', False, 'add text to baseframe instead of current frame')

#vd.charPalWidth = charPalWidth = 16
#vd.charPalHeight = charPalHeight = 16

vd.default_color = ''
vd.ddw_charset_index = 0
vd.clipboard_index = 0
vd.clipboard_pages = [list() for i in range(11)]


@VisiData.api
def open_ddw(vd, p):
    vd.timeouts_before_idle = 1000
    return DrawingSheet(p.name, source=p).drawing

vd.new_ddw = vd.open_ddw

@VisiData.api
def save_ddw(vd, p, *vsheets):
    # like save_jsonl but never emit explicit nulls; .ddw columns are fixed in DrawingSheet
    with p.open(mode='w', encoding=vsheets[0].options.save_encoding) as fp:
        if len(vsheets) > 1:
            vd.warning('ddw cannot save multiple sheets; concatenating all rows')
        for vs in vsheets:
            for row in vs.iterrows('saving'):
                fp.write(vd.encode_json(row, vs.visibleCols) + '\n')

@VisiData.lazy_property
def words(vd):
    return [x.strip() for x in open('/usr/share/dict/words').readlines() if 3 <= len(x) < 8 and x.islower() and x.strip().isalpha()]


@VisiData.api
def random_word(vd):
    try:
        return choice(vd.words)
    except FileNotFoundError:
        pass
    except Exception as e:
        vd.exceptionCaught(e)

    return 'unnamed'


def any_match(G1, G2):
    if G1 and G2:
        for g in G1:
            if g in G2: return True

def _parse_tags(tags):
    if isinstance(tags, list):
        return tags
    return (tags or '').split()

class DrawingSheet(JsonSheet):
    rowtype='elements'  # rowdef: { .type, .x, .y, .text, .color, .group, .tags='', .frame, .id, .rows=[] }
    columns=[
        ItemColumn('id', type=str),
        ItemColumn('type'),
        ItemColumn('x', type=int),
        ItemColumn('y', type=int),

        ItemColumn('text'),  # for text objects (type == '')
        ItemColumn('color', type=str), # for text

        # for all objects
        ItemColumn('tags', type=str),  # space-separated tag names
        ItemColumn('group'), # "
        ItemColumn('frame', type=str), # "

        ItemColumn('rows'), # for groups
        ItemColumn('duration_ms', type=int), # for frames

        ItemColumn('ref'),
    ]
    colorizers = [
        CellColorizer(3, None, lambda s,c,r,v: r and c and c.name == 'text' and r.color)
    ]
    def newRow(self):
        return AttrDict(x=None, y=None, text='', color='', tags='', group='')

    @functools.cached_property
    def drawing(self):
        return Drawing(self.name+".ddw", source=self)

    def addRow(self, row, **kwargs):
        # back-compat: legacy .ddw stored tags as a JSON list
        if isinstance(row.get('tags'), list):
            row['tags'] = ' '.join(row['tags'])
        assert not any(row is r for r in self.rows), 'duplicate row reference'  #61: remove when fixed
        row = super().addRow(row, **kwargs)
        vd.addUndo(self.rows.remove, row)
        self.setModified()
        return row

    def iterdeep(self, rows, x=0, y=0, parents=None):
        for r in rows:
            try:
                newparents = (parents or []) + [r]
                if r.type == 'frame': continue
                if r.ref:
                    assert r.type == 'ref'
                    g = self.groups[r.ref]
                    yield from self.iterdeep(g.rows, x+r.x, y+r.y, newparents)
                else:
                    yield r, x+r.x, y+r.y, newparents
                    yield from self.iterdeep(r.rows or [], x+r.x, x+r.y, newparents)
            except Exception as e:
                vd.exceptionCaught(e)

    def untag_rows(self, rows, s):
        col = self.column('tags')
        for row in Progress(rows):
            tags = [x for x in _parse_tags(col.getValue(row)) if x != s]
            col.setValue(row, ' '.join(tags))

    def tag_rows(self, rows, tagstr):
        newtags = tagstr.split()
        for r in rows:
            existing = _parse_tags(r.tags)
            for tag in newtags:
                if tag not in existing:
                    existing.append(tag)
            r.tags = ' '.join(existing)

    @property
    def groups(self):
        return {r.id:r for r in self.rows if r.type == 'group'}

    def create_group(self, gname):
        nr = self.newRow()
        nr.id = gname
        nr.type = 'group'
        vd.status('created group "%s"' % gname)
        return self.addRow(nr)

    def group_selected(self, gname):
        nr = self.create_group(gname)

        nr.rows = deepcopy(self.selectedRows)
        x1, y1, x2, y2 = boundingBox(nr.rows)
        nr.x, nr.y, nr.w, nr.h = x1, y1, x2-x1, y2-y1
        for r in nr.rows:
            r.x = (r.x or 0) - x1
            r.y = (r.y or 0) - y1

        def _undoGroupSelected(sheet, group):
            sheet.rows.pop(sheet.rows.index(group))

        self.deleteSelected()
        self.select([nr])

        vd.addUndo(_undoGroupSelected, self, nr)
        vd.status('group "%s" (%d objects)' % (gname, self.nSelectedRows))

    def regroup(self, rows):
        regrouped = []
        groups = set()  # that items were grouped into
        new_rows = deepcopy(rows)
        for r in new_rows:
            if r.group:
                regrouped.append(r)
                if r.group not in self.groups:
                    g = self.create_group(r.group)
                    g.x = r.x
                    g.y = r.y
                    self.addRow(g)
                else:
                    g = self.groups[r.group]

                r.x -= g.x
                r.y -= g.y
                g.rows.append(r)
                vd.addUndo(g.rows.pop, g.rows.index(r))
                groups.add(r.group)

        self.deleteBy(lambda r,rows=regrouped: r in rows)

        self.select(list(g for name, g in self.groups.items() if name in groups))

        vd.status('regrouped %d %s' % (len(regrouped), self.rowtype))

    def degroup(self, rows):
        degrouped = []
        groups = set()
        for row in rows:
          if row.type == 'ref':
            vd.warning("can't degroup reference (to '%s')" % row.ref)
            continue
          for r, x, y, parents in self.iterdeep([row]):
            r.x = x
            r.y = y
            r.group = '.'.join((p.id or '') for p in parents[:-1])

            if r.type == 'group':
                groups.add(r.id)

            if r is not parents[0]:
                self.addRow(r)
                degrouped.append(r)

        for g in groups:
            oldrows = copy(self.groups[g].rows)
            self.groups[g].rows.clear()
            vd.addUndo(self.regroup, oldrows)

        vd.status('ungrouped %d %s' % (len(degrouped), self.rowtype))
        return degrouped

    def gatherTag(self, gname):
        return list(r for r in self.rows if gname in _parse_tags(r.get('tags')))

    def slide_top(self, rows, index=0):
        'Move selected rows to top of sheet (bottom of drawing)'
        for r in rows:
            self.rows.pop(self.rows.index(r))
            self.rows.insert(index, r)

    def sort(self):
        vd.fail('sort disabled on drawing sheet')

    def save_txt(self, p, *sheets):
        dwg = self.drawing
        dwg.draw(None)
        with p.open_text(mode='w') as fp:
            for vs in sheets:
                line = ''
                maxX, maxY = dwg.maxXY
                for y in range(maxY+1):
                    for x in range(maxX+1):
                        r = dwg._displayedRows.get((x,y), None)
                        if r: line += r[-1].text[x-r[-1].x]
                        else: line += ' '
                    line = line.rstrip(' ') + '\n'

                    if line.strip():
                        fp.write(line)
                        line = ''
                    # if only newlines, let it ride


class Drawing(TextCanvas):
    rowtype = 'elements'  # rowdef: AttrDict (same as DrawingSheet)
    def iterbox(self, box, n=None, frames=None):
        'If *frames* is None, return top *n* elements from each cell within the given box (current frame falling back to base frame).  Otherwise return all elements from each cell within the given box (so base frame + current frame).  Otherwise return all elements that would be displayed in displayed in either If frames is None, uses actually displayed elements; otherwise, '
        ret = list()
        if frames is None:
            for ny in range(box.y1, box.y2-1):
                for nx in range(box.x1, box.x2-1):
                    for r in self._displayedRows[(nx,ny)][-(n or 0):]:
                        if r not in ret:
                            ret.append(r)
        else:
            for r in self.rows:
                if self.inFrame(r, frames):
                    if box.contains(CharBox(None, r.x, r.y, r.w or dispwidth(r.text or ''), r.h or 1)):
                        ret.append(r)

        return ret

    def __getattr__(self, k):
        if k == 'source' or self.source is self:
            return super().__getattr__(k)
        return getattr(self.source, k)

    @drawcache_property
    def selectedBox(self):
        x1, y1, x2, y2 = boundingBox(self.selectedRows)
        return CharBox(None, x1, y1, x2-x1, y2-y1)

    def elements(self, frames=None):
        'Return elements in *frames*.  If *frames* is None, then base image only.  Otherwise, *frames* must be a list of frame rows (like from .currentFrame or .frames).'
        return [r for r in self.rows if self.inFrame(r, frames)]

    def moveToRow(self, rowstr):
        a, b = map(int, rowstr.split())
        self.cursorBox.y1, self.cursorBox.y2 = a, b
        return True

    def moveToCol(self, colstr):
        a, b = map(int, colstr.split())
        self.cursorBox.x1, self.cursorBox.x2 = a, b
        return True

    def itercursor(self, n=None, frames=None):
        return self.iterbox(self.cursorBox, n=n, frames=frames)

    def autosave(self):
        try:
            now = time.time()
            autosave_interval_s = self.options.autosave_interval_s
            if autosave_interval_s and now-self.last_autosave > autosave_interval_s:
                p = Path(options.autosave_path)
                if not p.exists():
                    os.makedirs(p)
                vd.saveSheets(p/time.strftime(self.name+'-%Y%m%dT%H%M%S.ddw', time.localtime(now)), self, confirm_overwrite=False)
                self.last_autosave = now
        except Exception as e:
            vd.exceptionCaught(e)

    def draw(self, scr):
        self.autosave()
#        vd.getHelpPane('darkdraw', module='darkdraw').draw(scr, y=-1, x=-1)

        thisframe = self.handle_autoplay(self.currentFrame)

        self._displayedRows = defaultdict(list)  # (x, y) -> list of rows; actual screen layout (topmost last in list)
        self._tags = defaultdict(list)  # "tag" -> list of rows with that tag

        selectedGroups = set()  # any group with a selected element

        def draw_guides(xmax, ymax):
            if ymax < self.windowHeight-1:
                for x in range(xmax):
                    if x < self.windowWidth-1:
                        scr.addstr(ymax, x, '-')

            if xmax < self.windowWidth-1:
                for y in range(ymax):
                    if y < self.windowHeight-1:
                        scr.addstr(y, xmax, '|')

        #draw_guides(self.maxX+1, self.maxY+1)
        guidexy = self.options.disp_guide_xy
        if guidexy:
            try:
                guidex,guidey = map(int, guidexy.split())
                draw_guides(guidex, guidey)
            except Exception as e:
                vd.exceptionCaught(e)

        # draw blank cursor as backdrop but on top of guides
        for i in range(self.cursorBox.h):
            for j in range(self.cursorBox.w):
                y = self.cursorBox.y1+i-self.yoffset
                x = self.cursorBox.x1+j-self.xoffset
                clipdraw(scr, y, x, ' ', colors.color_current_row)

        for r, x, y, parents in self.iterdeep(self.source.rows):
            sy = y - self.yoffset
            sx = x - self.xoffset
            toprow = parents[0]
            rtags = _parse_tags(r.tags)
            for g in rtags:
                self._tags[g].append(r)

            if not r.text: continue
            if any_match(rtags, self.disabled_tags): continue
            if toprow.frame or r.frame:
                if not self.inFrame(r, [thisframe]): continue

            c = r.color or ''
            if self.cursorBox.contains(CharBox(scr, x, y, r.w or dispwidth(r.text), r.h or 1)):
                c = self.options.color_current_row + ' ' + str(c)
            if self.source.isSelected(toprow):
                c = self.options.color_selected_row + ' ' + str(c)
                if rtags: selectedGroups |= set(rtags)
            a = colors[c]

            if (0 <= sy < self.windowHeight-2 and 0 <= sx < self.windowWidth):  # inside screen
                w = clipdraw(scr, sy, sx, r.text, a)

            for i in range(0, dispwidth(r.text)):
                cellrows = self._displayedRows[(x+i, y)]
                if toprow not in cellrows:
                    cellrows.append(toprow)

        defcolor = self.options.color_default
        defattr = colors[defcolor]
        if self.options.visibility == 1: # draw tags
            clipdraw(scr, 0, self.windowWidth-20, '  00: (reset)  ', defattr)
            for i, tag in enumerate(self._tags.keys()):
                c = defcolor
                if tag in self.disabled_tags:
                    c = self.options.color_graph_hidden
                if self.cursorRow and tag in self.cursorRow.get('group', ''):
                    c = self.options.color_current_row + ' ' + c
                if tag in selectedGroups:
                    c = self.options.color_selected_row + ' ' + c
                clipdraw(scr, i+1, self.windowWidth-20, '  %02d: %7s  ' % (i+1, tag), colors[c])

        elif self.options.visibility == 2: # draw clipboard item shortcuts
            x += clipdraw(scr, 0, self.windowWidth-20, 'clipboard %d' % vd.clipboard_index, colors['underline'])
            for i, r in enumerate(vd.current_charset[:10]):
                x = self.windowWidth-20
                x += clipdraw(scr, i+1, x, '  %d: ' % (i+1), defattr)
                x += clipdraw(scr, i+1, x, r.text + '  ', colors[r.color])


        # draw lstatus2 (paste status with default color)
        y = self.windowHeight-2
        x = 3
        x += clipdraw(scr, y, x, f'paste {self.paste_mode} {"base" if self.options.ddw_add_baseframe else ""} ', defattr)

        x += clipdraw(scr, y, x, ' %s %s ' % (len(vd.getClipboardRows() or []), self.rowtype), defattr)

        x += clipdraw(scr, y, x, '  default color: ', defattr)
        x += clipdraw(scr, y, x, '##', colors[vd.default_color])
        x += clipdraw(scr, y, x, ' %s' % vd.default_color, defattr)

        x += 3
        x += clipdraw(scr, y, x, ' %s: ' % vd.clipboard_index, defattr)

        for i, r in enumerate(vd.current_charset[:10]):
            x += clipdraw(scr, y, x, str(i+1)[-1], defattr)
            x += clipdraw(scr, y, x, r.text, colors[vd.default_color])
            x += 1

        # draw rstatus2 (cursor status)
        if hasattr(self, 'cursorRows') and self.cursorRows:
            c = self.cursorRows[0].color
            x = self.windowWidth-30-len(c)
            x += clipdraw(scr, y, x, '%s  ' % c, defattr)
            x += clipdraw(scr, y, x, '##', colors[c])
            if self.cursorChar:
                x += clipdraw(scr, y, x, ' '+self.cursorChar[0], colors[c], w=3)
                x += clipdraw(scr, y, x, ' U+%04X' % ord(self.cursorChar[0]), defattr)

        x = self.windowWidth-16
        x += clipdraw(scr, y, x, '  %s' % self.cursorBox, defattr)

    @asyncthread
    def reload(self):
        self.source.ensureLoaded()
        vd.sync()
        if self._scr:
            self.draw(self._scr)

    def add_text(self, text, x, y, color=''):
        r = self.newRow()
        r.x, r.y, r.text, r.color = x, y, text, color
        if not self.options.ddw_add_baseframe:
            r.frame = self.currentFrame.id

        self.source.addRow(r)
        return r

    @property
    def hasBeenModified(self):
        return self.source.hasBeenModified

    @hasBeenModified.setter
    def hasBeenModified(self, v:bool):
        if self.source:
            self.source.hasBeenModified = v

    def place_text(self, text, box, dx=0, dy=0, go_forward=True, color=None):
        'Return (width, height) of drawn text.'
        self.add_text(text, box.x1, box.y1, color or vd.default_color)

        if go_forward:
            self.go_forward(dispwidth(text)+dx, 1+dy)

    def place_text_n(self, box, n):
        if self.paste_mode == "color":
            self.set_color(vd.current_charset[n].color, self.cursorRows)
            return

        text = vd.current_charset[n].text
        if self.paste_mode == "char":
            self.place_text(text, box)
        else:  # 'all' - preserve source color even when empty (do not coerce to default_color)
            self.add_text(text, box.x1, box.y1, vd.current_charset[n].color)
            self.go_forward(dispwidth(text), 1)

    def edit_text(self, text, row):
        if row is None:
            self.place_text(text, self.cursorBox, dx=1)
            return
        oldtext = row.text
        row.text = text
        vd.addUndo(setattr, row, 'text', oldtext)


    def get_text(self, x=None, y=None):
        'Return text of topmost visible element at (x,y) (or cursor if not given).'
        if x is None: x = self.cursorBox.x1
        if y is None: y = self.cursorBox.y1
        r = self._displayedRows.get((x,y), None)
        if not r: return ''
        return r[-1]['text'][x-r[-1].x]

    def remove_at(self, box):
        rows = list(self.iterbox(box))
        self.source.deleteBy(lambda r,rows=rows: r in rows)
        return rows

    @property
    def cursorRows(self):
        return list(self.iterbox(self.cursorBox))

    @property
    def topCursorRows(self):
        return list(self.iterbox(self.cursorBox, n=1))

    @property
    def cursorRow(self):
        cr = self.cursorRows
        if cr: return cr[-1]

    @property
    def cursorChar(self):
        cr = self.cursorRow
        if cr: return cr.get('text', '')
        return ''

    @property
    def cursorDesc(self):
        cr = self.cursorRow
        if cr and cr.text:
            return 'U+%04X' % ord(cr.text[0])
        if cr and cr.type == 'group':
            n = len(list(self.iterdeep(cr.rows)))
            return '%s (%s objects)' % (cr.id, n)
        return '???'

    @property
    def cursorCharName(self):
        ch = self.cursorChar
        if not ch: return ''
        return unicodedata.name(ch[0])

    def go_left(self):
        if self.options.pen_down:
            self.pendir = 'l'
            self.place_text(ch, self.cursorBox, **vd.getClipboardRows()[0])
        else:
            self.cursorBox.x1 = max(0, self.cursorBox.x1-1)

    def go_right(self):
        if self.options.pen_down:
            self.pendir = 'r'
            self.place_text(ch, self.cursorBox, **vd.getClipboardRows()[0])
        else:
            self.cursorBox.x1 += 1

    def go_down(self):
        if self.options.pen_down:
            self.pendir = 'd'
            self.place_text(ch, self.cursorBox, **vd.getClipboardRows()[0])
        else:
            self.cursorBox.y1 += 1

    def go_up(self):
        if self.options.pen_down:
            self.pendir = 'u'
            self.place_text(ch, self.cursorBox, **vd.getClipboardRows()[0])
        else:
            self.cursorBox.y1 = max(0, self.cursorBox.y1-1)

    def go_pagedown(self, n):
        dy = n*(self.windowHeight-3)
        self.cursorBox.y1 += dy
        self.yoffset += dy

    def go_leftmost(self):
        self.cursorBox.x1 = 0
        self.xoffset = 0

    def go_rightmost(self):
        self.cursorBox.x1, _ = self.maxXY
        self.xoffset = max(0, self.cursorBox.x1 - self.windowWidth + 2)

    def go_top(self):
        self.cursorBox.y1 = 0
        self.yoffset = 0

    def go_bottom(self):
        _, self.cursorBox.y1 = self.maxXY
        self.yoffset = max(0, self.cursorBox.y1 - self.windowHeight + 2)

    def go_forward(self, x, y):
        if self.pendir == 'd': self.cursorBox.y1 += y
        elif self.pendir == 'u': self.cursorBox.y1 -= y
        elif self.pendir == 'r': self.cursorBox.x1 += x
        elif self.pendir == 'l': self.cursorBox.x1 -= x

    def go_obj(self, xdir=0, ydir=0):
        x=self.cursorBox.x1
        y=self.cursorBox.y1
        currows = self._displayedRows.get((x, y), [])
        xmin = min(x for x, y in self._displayedRows.keys())
        ymin = min(y for x, y in self._displayedRows.keys())
        xmax = max(x for x, y in self._displayedRows.keys())
        ymax = max(y for x, y in self._displayedRows.keys())

        while xmin <= x <= xmax and ymin <= y <= ymax:
            for r in self._displayedRows.get((x, y), [])[::-1]:
                if r and r not in currows:
                    self.cursorBox.x1 = x
                    self.cursorBox.y1 = y
                    return
            x += xdir
            y += ydir

    def checkCursor(self):
        # super().checkCursor()
        self.yoffset = max(0, self.yoffset)
        self.xoffset = max(0, self.xoffset)
        self.cursorBox.y1 = max(0, self.cursorBox.y1)
        self.cursorBox.x1 = max(0, self.cursorBox.x1)
        self.cursorBox.w = max(0, self.cursorBox.w)
        self.cursorBox.h = max(0, self.cursorBox.h)

        if self.cursorBox.y1 < self.yoffset:
            self.yoffset = self.cursorBox.y1
        elif self.cursorBox.y1 > self.yoffset + self.windowHeight-3:
            self.yoffset = self.cursorBox.y1 - self.windowHeight+3

        if self.cursorBox.x1 < self.xoffset:
            self.xoffset = self.cursorBox.x1
        elif self.cursorBox.x1 >= self.xoffset + self.windowWidth-2:
            self.xoffset = self.cursorBox.x1 - self.windowWidth+2

    def cycle_paste_mode(self):
        modes = ['all', 'char', 'color']
        self.paste_mode = modes[(modes.index(self.paste_mode)+1)%len(modes)]

    def fill_chars(self, srcrows, box, n=None):
        it = itertools.cycle(srcrows or vd.fail("no clipboard to fill with"))
        newrows = []
        nfilled = 0
        niters = 0
        for newy in range(box.y1, box.y1+box.h):
            newx = box.x1
            while newx < box.x1+box.w and niters < 10000:
                niters += 1
                oldr = next(it)
                if self.paste_mode in ('all', 'char'):
                    r = self.newRow()
                    r.update(deepcopy(oldr))
                    r.x, r.y = newx, newy
                    r.text = oldr.text
                    r.frame = None if self.options.ddw_add_baseframe else self.currentFrame.id
                    if self.paste_mode == 'char':
                        r.color = vd.default_color
                    newrows.append(r)
                    nfilled += 1
                    self.source.addRow(r)
                elif self.paste_mode == 'color':
                    if oldr.color and newx < box.x2 and newy < box.y2-1:
                        for existing in self._displayedRows[(newx, newy)][-(n or 0):]:
                            nfilled += 1
                            existing.color = oldr.color
                newx += dispwidth(oldr.text)

        vd.status(f'filled {nfilled} cells')
        if nfilled == 0:
            vd.warning(f'paste mode {self.paste_mode} had nothing to fill')

    def paste_chars(self, srcrows, box, n=None):
        # n is number of rows deep to change color
        srcrows or vd.fail('no rows to paste')

        newrows = []
        npasted = 0
        frameset = set(r.frame for r in srcrows)
        x1, y1, x2, y2 = boundingBox(srcrows)
        for oldr in srcrows:
            if oldr.x is None:
                newx = box.x1
                newy = box.y1
                if len(srcrows) > 1:
                    self.go_forward(dispwidth(oldr.text)+1, 1)
            else:
                newx = (oldr.x or 0)+box.x1-x1
                newy = (oldr.y or 0)+box.y1-y1

            if self.paste_mode in 'all char':
                r = self.newRow()
                r.update(deepcopy(oldr))
                if self.options.ddw_add_baseframe:
                    r.frame = None
                elif oldr.frame not in [f.id for f in self.frames]:
                    r.frame = None
                elif len(frameset) == 1:  # if all characters are only in a single frame, add to current frame instead
                    r.frame = self.currentFrame.id
                # else use paste to their existing frame

                r.text = oldr.text
                r.x, r.y = newx, newy
                if self.paste_mode == 'char':
                    r.color = vd.default_color
                newrows.append(r)
                self.source.addRow(r)
                npasted += 1
            elif self.paste_mode == 'color':
                if oldr.color and newx < box.x2 and newy < box.y2-1:
                    for existing in self._displayedRows[(newx, newy)][-(n or 0):]:
                        npasted += 1
                        oldcolor = existing.color
                        existing.color = oldr.color
                        vd.addUndo(setattr, existing, 'color', oldcolor)

        if npasted == 0:
            vd.warning(f'paste mode {self.paste_mode} had nothing to paste')

    def paste_special(self):
        if self.paste_mode == 'color':  # top only
            return self.paste_chars(vd.getClipboardRows(), self.cursorBox, n=1)

        for r in vd.getClipboardRows():
            if r.type == 'group':
                newr = self.newRow()
                newr.type = 'ref'
                newr.x, newr.y = self.cursorBox.x1, self.cursorBox.y1
                newr.ref = r.id
                self.addRow(newr)
            elif r.type:
                vd.status('ignoring %s type row' % r.type)

    def select_tag(self, tag):
        self.select(list(r for r in self.source.rows if tag in _parse_tags(r.tags)))

    def unselect_tag(self, tag):
        self.unselect(list(r for r in self.rows if tag in _parse_tags(r.tags)))

    def align_selected(self, attrname):
        rows = self.someSelectedRows
        for r in rows:
            r.x = rows[0].x


@VisiData.api
def getClipboardRows(vd):
    return vd.clipboard_pages[vd.clipboard_index]

@VisiData.api
def setClipboardRows(vd, rows):
    vd.clipboard_pages[vd.clipboard_index] = rows


@Drawing.api
def input_canvas(sheet, box, row=None):
    kwargs = {}
    if row:
        x, y = row.x-sheet.xoffset, row.y-sheet.yoffset
        kwargs['value'] = row.text
        kwargs['i'] = box.x1-x
    else:
        x, y = box.x1-sheet.xoffset, box.y1-sheet.yoffset

    return vd.editText(y, x, sheet.windowWidth-x, fillchar='', clear=False, **kwargs)


@Drawing.api
def cycle_color(sheet, rows, n=1):
    for r in rows:
       clist = []
       for c in (r.color or '').split():
           try:
                c = str((int(c)+n) % 256)
           except Exception:
                pass
           clist.append(c)
       r.color = ''.join(clist)


@Drawing.api
def set_color(self, color, rows):
    for r in rows:
        oldcolor = copy(r.color)
        r.color = color
        vd.addUndo(setattr, r, 'color', oldcolor)

@Drawing.api
def generate_sauce(sheet):
    from .ansi import default_sauce_rows
    maxX, maxY = sheet.maxXY
    sheet.source.deleteBy(lambda r: (r.get('frame') or '') == 'SAUCE_record')
    for i, r in enumerate(default_sauce_rows(maxX, maxY)):
        sheet.source.addRow(AttrDict(r), index=i)
    vd.status(f'SAUCE record generated ({maxX+1}x{maxY+1})')

@Drawing.api
def select_top(sheet, box):
    r = []
    for x in range(box.x1, box.x2-1):
        for y in range(box.y1, box.y2-1):
            vd.status(x,y)
            rows = sheet._displayedRows[(x,y)]
            if rows:
                r.append(rows[-1])
    sheet.select(r)

@VisiData.property
def current_charset(vd):
    return vd.getClipboardRows()

@VisiData.api
def boxchar(vd, ch):
    return AttrDict(x=0, y=0, text=ch, color=vd.default_color)


@Drawing.command('', 'box-cursor', 'draw a box to fill the inner edge of the cursor')
def box_cursor(sheet):
    pass


Drawing.init('cursorBox', lambda: CharBox(None, 0,0,1,1))
Drawing.init('_displayedRows', dict)  # (x,y) -> list of rows
Drawing.init('pendir', lambda: 'r')
Drawing.init('disabled_tags', set)  # set of groupnames which should not be drawn or interacted with

Drawing.init('mark', lambda: (0,0))
Drawing.init('paste_mode', lambda: 'all')
Drawing.init('last_autosave', int)

# (xoffset, yoffset) is absolute coordinate of upper left of viewport (0, 0)
Drawing.init('yoffset', int)
Drawing.init('xoffset', int)

Drawing.class_options.disp_rstatus_fmt='{sheet.source.nRows} {sheet.rowtype}  {sheet.options.disp_selected_note}{sheet.source.nSelectedRows}'
Drawing.class_options.quitguard='modified'
Drawing.class_options.null_value=''
DrawingSheet.class_options.null_value=''

Drawing.tutorial_url='https://raw.githubusercontent.com/devottys/studio/master/darkdraw-tutorial.ddw'


Drawing.addCommand(None, 'go-left',  'go_left()', 'go left one char', replay=False)
Drawing.addCommand(None, 'go-down',  'go_down()', 'go down one char', replay=False)
Drawing.addCommand(None, 'go-up',   'go_up()', 'go up one char', replay=False)
Drawing.addCommand(None, 'go-right', 'go_right()', 'go right one char in the palette', replay=False)
Drawing.addCommand(None, 'go-pagedown', 'go_pagedown(+1);', 'scroll one page forward', replay=False)
Drawing.addCommand(None, 'go-pageup', 'go_pagedown(-1)', 'scroll one page backward', replay=False)

Drawing.addCommand(None, 'go-leftmost', 'go_leftmost()', 'go all the way to the left', replay=False)
Drawing.addCommand(None, 'go-top', 'go_top()', 'go all the way to the top', replay=False)
Drawing.addCommand(None, 'go-bottom', 'go_bottom()', 'go all the way to the bottom', replay=False)
Drawing.addCommand(None, 'go-rightmost', 'go_rightmost()', 'go all the way to the right', replay=False)

Drawing.addCommand('', 'pen-left', 'sheet.pendir="l"', '')
Drawing.addCommand('', 'pen-down', 'sheet.pendir="d"', '')
Drawing.addCommand('', 'pen-up', 'sheet.pendir="u"', '')
Drawing.addCommand('', 'pen-right', 'sheet.pendir="r"', '')

Drawing.addCommand('', 'align-x-selected', 'align_selected("x")')

Drawing.addCommand('gHome', 'slide-top-selected', 'source.slide_top(source.someSelectedRows, -1)', 'move selected items to top layer of drawing')
Drawing.addCommand('gEnd', 'slide-bottom-selected', 'source.slide_top(source.someSelectedRows, 0)', 'move selected items to bottom layer of drawing')
Drawing.addCommand('d', 'delete-cursor', 'remove_at(cursorBox)', 'delete first item under cursor')
Drawing.addCommand('gd', 'delete-selected', 'source.deleteSelected()', 'delete selected rows on source sheet')
Drawing.addCommand('a', 'add-input', 'place_text(input_canvas(cursorBox, None), cursorBox)', 'place text string at cursor')
Drawing.addCommand('e', 'edit-text', 'r=cursorRow; edit_text(input_canvas(cursorBox, r), r)')
Drawing.addCommand('ge', 'edit-selected', 'v=input("text: ", value=get_text())\nfor r in source.selectedRows: r.text=v')
Drawing.addCommand('y', 'yank-char', 'sheet.copyRows(cursorRows)')
Drawing.addCommand('gy', 'yank-selected', 'sheet.copyRows(sheet.selectedRows)')
Drawing.addCommand('x', 'cut-char', 'sheet.copyRows(remove_at(cursorBox))')
Drawing.addCommand('zx', 'cut-char-top', 'r=list(itercursor())[-1]; sheet.copyRows([r]); source.deleteBy(lambda r,row=r: r is row)')
Drawing.addCommand('p', 'paste-chars', 'sheet.paste_chars(vd.getClipboardRows(), cursorBox)')
Drawing.addCommand('zp', 'paste-special', 'sheet.paste_special()')
Drawing.addCommand('f', 'fill-chars', 'sheet.fill_chars(vd.getClipboardRows(), cursorBox)', 'fill cursor with clipboard items')

Drawing.addCommand('zh', 'go-left-obj', 'go_obj(-1, 0)')
Drawing.addCommand('zj', 'go-down-obj', 'go_obj(0, +1)')
Drawing.addCommand('zk', 'go-up-obj', 'go_obj(0, -1)')
Drawing.addCommand('zl', 'go-right-obj', 'go_obj(+1, 0)')

Drawing.addCommand('g)', 'group-selected', 'sheet.group_selected(input("group name: ", value=random_word()))')
Drawing.addCommand('g(', 'degroup-selected-temp', 'degrouped = sheet.degroup(source.someSelectedRows); source.clearSelected(); source.select(degrouped)')
Drawing.addCommand('gz(', 'degroup-selected-perm', 'sheet.degroup_all()')
Drawing.addCommand('gz)', 'regroup-selected', 'sheet.regroup(source.someSelectedRows)')
DrawingSheet.addCommand('g)', 'group-selected', 'sheet.group_selected(input("group name: ", value=random_word()))')
DrawingSheet.addCommand('g(', 'degroup-selected-perm', 'sheet.degroup_all()')
DrawingSheet.addCommand('gz(', 'degroup-selected-temp', 'degroup = sheet.degroup(someSelectedRows); clearSelected(); select(degrouped)')
DrawingSheet.addCommand('gz)', 'regroup-selected', 'sheet.regroup(someSelectedRows)')

Drawing.addCommand('zs', 'select-top', 'select_top(cursorBox)')
Drawing.addCommand(',', 'select-equal-char', 'sheet.select(list(source.gatherBy(lambda r,ch=cursorChar: r.text==ch)))')
Drawing.addCommand('|', 'select-tag', 'sheet.select_tag(input("select tag: ", type="group"))')
Drawing.addCommand('\\', 'unselect-tag', 'sheet.unselect_tag(input("unselect tag: ", type="group"))')

Drawing.addCommand('gs', 'select-all', 'source.select(itercursor(frames=source.frames))')
Drawing.addCommand('gt', 'toggle-all', 'source.toggle(itercursor(frames=source.frames))')

Drawing.addCommand('z00', 'enable-all-groups', 'disabled_tags.clear()')
for i in range(1, 10):
    Drawing.addCommand('%02d'%i, 'toggle-enabled-group-%s'%i, 'g=list(_tags.keys())[%s]; disabled_tags.remove(g) if g in disabled_tags else disabled_tags.add(g)' %(i-1))
    Drawing.addCommand('g%02d'%i, 'select-group-%s'%i, 'g=list(_tags.keys())[%s]; source.select(source.gatherTag(g))' %(i-1))
    Drawing.addCommand('z%02d'%i, 'unselect-group-%s'%i, 'g=list(_tags.keys())[%s]; source.unselect(source.gatherTag(g))' %(i-1))

Drawing.addCommand('A', 'new-drawing', 'vd.push(vd.new_ddw(Path(vd.random_word()+".ddw")))', 'open blank drawing')
Drawing.addCommand('M', 'open-unicode', 'vd.push(vd.unibrowser)', 'open unicode character table')
Drawing.addCommand('`', 'push-source', 'vd.push(sheet.source)', 'push backing sheet for this drawing')
DrawingSheet.addCommand('`', 'open-drawing', 'vd.push(sheet.drawing)', 'push drawing for this backing sheet')

Drawing.addCommand('Ctrl+G', 'show-char', 'status(f"{sheet.cursorBox} <{cursorDesc}> {sheet.cursorCharName}")')
DrawingSheet.addCommand('Enter', 'dive-group', 'cursorRow.rows or fail("no elements in group"); vd.push(DrawingSheet(source=sheet, rows=cursorRow.rows))')
DrawingSheet.addCommand('gEnter', 'dive-selected', 'ret=sum(((r.rows or []) for r in selectedRows), []) or fail("no groups"); vd.push(DrawingSheet(source=sheet, rows=ret))')

Drawing.addCommand('gc', 'set-default-color-input', 'vd.default_color=input("set default color: ", value=vd.default_color)')
Drawing.addCommand('c', 'set-default-color', 'vd.default_color=list(itercursor())[-1].color')
Drawing.addCommand('zc', 'set-color-input', 'set_color(input("color: ", value=vd.default_color), cursorRows)')
Drawing.addCommand('gzc', 'set-color-input-selected', 'set_color(input("color: ", value=vd.default_color), sheet.selectedRows)')

Drawing.addCommand('<', 'cycle-cursor-prev', 'cycle_color(cursorRows, -1)')
Drawing.addCommand('>', 'cycle-cursor-next', 'cycle_color(cursorRows, 1)')
Drawing.addCommand('g<', 'color-selected-prev', 'cycle_color(selectedRows, -1)')
Drawing.addCommand('g>', 'color-selected-next', 'cycle_color(selectedRows, 1)')
Drawing.addCommand('z<', 'cycle-topcursor-prev', 'cycle_color(topCursorRows, -1)')
Drawing.addCommand('z>', 'cycle-topcursor-next', 'cycle_color(topCursorRows, 1)')

Drawing.addCommand('g+', 'tag-selected', 'sheet.tag_rows(sheet.someSelectedRows, vd.input("tag selected as: ", type="tag"))')
Drawing.addCommand('+', 'tag-cursor', 'sheet.tag_rows(sheet.cursorRows, vd.input("tag cursor as: ", type="tag"))')
Drawing.addCommand('z+', 'tag-topcursor', 'sheet.tag_rows(sheet.topCursorRows, vd.input("tag top of cursor as: ", type="tag"))')

Drawing.addCommand('-', 'untag-cursor', 'sheet.untag_rows(sheet.cursorRows, vd.input("untag cursor as: ", type="tag"))')
Drawing.addCommand('g-', 'untag-selected', 'sheet.untag_rows(sheet.someSelectedRows, vd.input("untag selected as: ", type="tag"))')
Drawing.addCommand('z-', 'untag-topcursor', 'sheet.untag_rows(sheet.topCursorRows, vd.input("untag top of cursor as: ", type="tag"))')

Drawing.addCommand('{', 'go-prev-selected', 'source.moveToNextRow(lambda row,source=source: source.isSelected(row), reverse=True) or fail("no previous selected row"); sheet.cursorBox.x1=source.cursorRow.x; sheet.cursorBox.y1=source.cursorRow.y', 'go to previous selected row'),
Drawing.addCommand('}', 'go-next-selected', 'source.moveToNextRow(lambda row,source=source: source.isSelected(row)) or fail("no next selected row"); sheet.cursorBox.x1=source.cursorRow.x; sheet.cursorBox.y1=source.cursorRow.y', 'go to next selected row'),
Drawing.addCommand('zCtrl+Y', 'pyobj-cursor', 'vd.push(PyobjSheet("cursor_top", source=cursorRow))')
Drawing.addCommand('Ctrl+Y', 'pyobj-cursor', 'vd.push(PyobjSheet("cursor", source=cursorRows))')

Drawing.addCommand('Ctrl+S', 'save-sheet', 'vd.saveSheets(inputPath("save to: ", value=source.getDefaultSaveName()), sheet.source)', 'save current drawing')
Drawing.addCommand('i', 'insert-row', 'for r in source.someSelectedRows: r.y += (r.y >= cursorBox.y1)', '')
Drawing.addCommand('zi', 'insert-col', 'for r in source.someSelectedRows: r.x += (r.x >= cursorBox.x1)', '')

Drawing.addCommand('zm', 'place-mark', 'sheet.mark=(cursorBox.x1, cursorBox.y1)')
Drawing.addCommand('m', 'swap-mark', '(cursorBox.x1, cursorBox.y1), sheet.mark=sheet.mark, (cursorBox.x1, cursorBox.y1)')
Drawing.addCommand('v', 'visibility', 'options.visibility = (options.visibility+1)%3')

Drawing.addCommand(';', 'cycle-paste-mode', 'sheet.cycle_paste_mode()')
Drawing.addCommand('g;', 'set-paste-base', 'sheet.options.ddw_add_baseframe = not sheet.options.ddw_add_baseframe')
Drawing.addCommand('Ctrl+G', 'toggle-help', 'vd.options.show_help = not vd.options.show_help')

Drawing.addCommand('Alt+[', 'cycle-char-palette-down', 'vd.clipboard_index = (vd.clipboard_index - 1) % len(vd.clipboard_pages)')
Drawing.addCommand('Alt+]', 'cycle-char-palette-up', 'vd.clipboard_index = (vd.clipboard_index + 1) % len(vd.clipboard_pages)')

for i in range(1, 11):
    Drawing.addCommand(f'F{i}', f'paste-char-{i}', f'place_text_n(cursorBox, {i-1})', '')

for i in range(0, 11):
    Drawing.addCommand(f'zF{i}', f'set-clipboard-page-{i}', f'vd.clipboard_index = {i}')

Drawing.bindkey('zRight', 'resize-cursor-wider')
Drawing.bindkey('zLeft', 'resize-cursor-thinner')
Drawing.bindkey('zUp', 'resize-cursor-shorter')
Drawing.bindkey('zDown', 'resize-cursor-taller')

Drawing.bindkey('C', 'open-colors')
Drawing.unbindkey('Ctrl+R')

BaseSheet.addCommand(None, 'open-tutorial-darkdraw', 'vd.push(openSource(Drawing.tutorial_url))', 'Download and open DarkDraw tutorial as a DarkDraw sheet')
Drawing.addCommand(None, 'generate-sauce', 'sheet.generate_sauce()', 'generate SAUCE metadata rows for current drawing')

vd.addMenuItems('''
    File > New drawing > new-drawing
    View > Unicode browser > open-unicode
    View > Drawing table > open-drawing
    Help > DarkDraw tutorial > open-tutorial-darkdraw
    Edit > Add text > add-input
    DarkDraw > New drawing > new-drawing
    DarkDraw > View > Colors sheet > open-colors
    DarkDraw > View > Unicode characters > open-unicode
    DarkDraw > View > Backing table > open-backing
    DarkDraw > Cycle paste mode > cycle-paste-mode
    DarkDraw > Color > Set default from cursor > set-default-cursor
    DarkDraw > Color > Set to input > set-color-input
    DarkDraw > Color > Cycle > cursor > down > cycle-cursor-next
    DarkDraw > Color > Cycle > cursor > up > cycle-cursor-prev
    DarkDraw > Color > Cycle > selected > down > color-selected-next
    DarkDraw > Color > Cycle > selected > up > color-selected-prev
    DarkDraw > Color > Cycle > top of cursor > down > cycle-topcursor-next
    DarkDraw > Color > Cycle > top of cursor > up > cycle-topcursor-prev
    DarkDraw > Tag > selected > tag-selected
    DarkDraw > Tag > under cursor > tag-cursor
    DarkDraw > Tag > top of cursor > tag-topcursor
    DarkDraw > Insert > Line > insert-row
    DarkDraw > Insert > Character > insert-col
''')
