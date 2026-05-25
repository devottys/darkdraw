from copy import copy as _copy

from visidata import vd, VisiData

from .drawing import DrawingSheet, Drawing


### NEW-FRAME ################################################################
@DrawingSheet.api
def new_between_frame(self, fidx1, fidx2):
    f1 = f2 = None
    if not self.frames:
        base = '0'
    else:
        if 0 <= fidx1 < len(self.frames):
            f1 = self.frames[fidx1]
        if 0 <= fidx2 < len(self.frames):
            f2 = self.frames[fidx2]
        if f1 and f2:
            base = str(f1.id)+'-'+str(f2.id)
        elif f1:
            try: base = str(int(f1.id)+1)
            except ValueError: base = f'{f1.id}-post'
        elif f2:
            try: base = str(int(f2.id)-1)
            except ValueError: base = f'{f2.id}-pre'

    existing = {r.id for r in self.rows if r.type == 'frame'}
    name = base
    i = 2
    while name in existing:
        name = f'{base}-{i}'
        i += 1

    newf = self.newRow()
    newf.type = 'frame'
    newf.id = name
    newf.duration_ms = 100
    if f1:
        for i, r in enumerate(self.rows):
            if r is f1:
                vd.clearCaches()
                self.addRow(newf, index=i+1)
                break
        return newf
    else:
        vd.clearCaches()
        return self.addRow(newf, index=0)
##############################################################################

### DUPLICATE-FRAME ##########################################################
@DrawingSheet.api
def duplicate_frame(self, fidx, before=False):
    if not self.frames:
        return self.new_between_frame(-1, 0)

    cur = self.frames[fidx]
    if before:
        adj = self.frames[fidx-1] if fidx > 0 else None
        if adj:
            base = str(adj.id)+'-'+str(cur.id)
        else:
            try: base = str(int(cur.id)-1)
            except ValueError: base = f'{cur.id}-pre'
    else:
        adj = self.frames[fidx+1] if fidx+1 < len(self.frames) else None
        if adj:
            base = str(cur.id)+'-'+str(adj.id)
        else:
            try: base = str(int(cur.id)+1)
            except ValueError: base = f'{cur.id}-post'

    existing = {r.id for r in self.rows if r.type == 'frame'}
    name = base
    i = 2
    while name in existing:
        name = f'{base}-{i}'
        i += 1

    newf = self.newRow()
    newf.type = 'frame'
    newf.id = name
    newf.duration_ms = cur.duration_ms or 100

    for i, r in enumerate(self.rows):
        if r is cur:
            vd.clearCaches()
            self.addRow(newf, index=i if before else i+1)
            break

    dup_rows = [_copy(r) for r in self.rows if cur.id in (r.frame or '').split()]
    for r in dup_rows:
        r.frame = newf.id
        self.addRow(r)
    return newf

Drawing.addCommand('gz[', 'duplicate-frame-before', 'sheet.source.duplicate_frame(sheet.cursorFrameIndex, before=True)', 'insert new frame before current with copy of current frame objects')
Drawing.addCommand('gz]', 'duplicate-frame-after', 'sheet.source.duplicate_frame(sheet.cursorFrameIndex, before=False); sheet.cursorFrameIndex += 1', 'insert new frame after current with copy of current frame objects')
##############################################################################

### PRUNE UNUSED ##############################################
@DrawingSheet.api
def prune_unused(self):
    'Delete elements whose .frame references no existing frame id.'
    valid = {r.id for r in self.rows if r.type == 'frame'}
    orphans = [r for r in self.rows
               if not r.type and r.frame
               and not (set(r.frame.split()) & valid)]
    if not orphans:
        vd.status('no orphans')
        return
    oids = set(map(id, orphans))
    self.deleteBy(lambda r, oids=oids: id(r) in oids)
    vd.status(f'deleted {len(orphans)} orphan(s)')

DrawingSheet.addCommand(None, 'prune-unused', 'sheet.prune_unused()', 'delete elements whose frame field references no existing frame')
Drawing.addCommand(None, 'prune-unused', 'sheet.source.prune_unused()', 'delete elements whose frame field references no existing frame')
##############################################################################

### DEDUPLICATE TEXT ###################################################
@DrawingSheet.api
def deduplicate_text(self):
    'Merge elements sharing x,y,text,color,tags,group: union their frame ids onto one, delete the rest.'
    groups = {}
    for r in self.rows:
        if r.type: continue
        key = (r.x, r.y, r.text, r.color, frozenset((r.tags or '').split()), r.group)
        groups.setdefault(key, []).append(r)

    to_delete = []
    merged = 0
    for rs in groups.values():
        if len(rs) < 2: continue
        frames = set()
        any_empty = False
        for r in rs:
            if not r.frame:
                any_empty = True
            else:
                frames.update(r.frame.split())
        keeper = rs[0]
        new_frame = '' if any_empty else ' '.join(sorted(frames))
        if keeper.frame != new_frame:
            vd.addUndo(setattr, keeper, 'frame', keeper.frame)
            keeper.frame = new_frame
        to_delete.extend(rs[1:])
        merged += 1

    if not to_delete:
        vd.status('no duplicates')
        return
    oids = set(map(id, to_delete))
    self.deleteBy(lambda r, oids=oids: id(r) in oids)
    vd.status(f'combined {merged} group(s), removed {len(to_delete)} duplicate(s)')

DrawingSheet.addCommand(None, 'deduplicate-text', 'sheet.deduplicate_text()', 'merge elements with same x,y,text,color,tags,group: union frame ids, delete extras')
Drawing.addCommand(None, 'deduplicate-text', 'sheet.source.deduplicate_text()', 'merge elements with same x,y,text,color,tags,group: union frame ids, delete extras')
##############################################################################

### deDUPLICATE-FRAMES #################################################
@DrawingSheet.api
def deduplicate_frames(self):
    'Replace later duplicate frames with another instance of the first matching frame. Frames are identical when their element sets share the same x,y,text,color,tags,group.'
    frames = [r for r in self.rows if r.type == 'frame']
    if len(frames) < 2:
        vd.status('not enough frames')
        return

    def elem_key(r):
        return (r.x, r.y, r.text, r.color, frozenset((r.tags or '').split()), r.group)

    def frame_sig(fid):
        return frozenset(elem_key(r) for r in self.rows
                         if not r.type and fid in (r.frame or '').split())

    sigs = {}
    merges = []
    for f in frames:
        s = frame_sig(f.id)
        if not s: continue
        if s in sigs:
            merges.append((sigs[s], f))
        else:
            sigs[s] = f

    if not merges:
        vd.status('no duplicate frames')
        return

    to_delete = []
    for first, dup in merges:
        old_id = dup.id
        for r in self.rows:
            if r.type: continue
            ids = (r.frame or '').split()
            if old_id not in ids: continue
            if ids == [old_id]:
                to_delete.append(r)
            else:
                vd.addUndo(setattr, r, 'frame', r.frame)
                r.frame = ' '.join(x for x in ids if x != old_id)
        vd.addUndo(setattr, dup, 'id', old_id)
        dup.id = first.id

    if to_delete:
        oids = set(map(id, to_delete))
        self.deleteBy(lambda r, oids=oids: id(r) in oids)
    vd.clearCaches()
    vd.status(f'replaced {len(merges)} duplicate frame(s)')

DrawingSheet.addCommand(None, 'deduplicate-frames', 'sheet.deduplicate_frames()', 'replace later duplicate frames with another instance of the first matching frame')
Drawing.addCommand(None, 'deduplicate-frames', 'sheet.source.deduplicate_frames()', 'replace later duplicate frames with another instance of the first matching frame')
##############################################################################

### SELF-CONTAIN FRAMES ######################################################
@DrawingSheet.api
def self_contain_frames(self):
    'Split each element with >1 frame ids into one copy per frame; delete originals. Skips empty/null frame field.'
    to_delete = []
    new_rows = []
    n_split = 0
    for r in list(self.rows):
        if r.type: continue
        if not r.frame: continue
        ids = r.frame.split()
        if len(ids) < 2: continue
        for fid in ids:
            new_r = _copy(r)
            new_r.frame = fid
            self.addRow(new_r)
            new_rows.append(new_r)
        to_delete.append(r)
        n_split += 1
    if not to_delete:
        vd.status('no multi-frame elements')
        return
    oids = set(map(id, to_delete))
    self.deleteBy(lambda r, oids=oids: id(r) in oids)
    vd.status(f'split {n_split} element(s) into {len(new_rows)} copies')

DrawingSheet.addCommand(None, 'self-contain-frames', 'sheet.self_contain_frames()', 'split each multi-frame element into one copy per frame; delete originals')
Drawing.addCommand(None, 'self-contain-frames', 'sheet.source.self_contain_frames()', 'split each multi-frame element into one copy per frame; delete originals')
##############################################################################
