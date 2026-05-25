import time

from visidata import Sheet, ItemColumn, vd, AttrDict

from .drawing import Drawing, DrawingSheet


class FramesSheet(Sheet):
    rowtype='frames'  # rowdef: { .type, .id, .duration_ms, .x, .y }
    columns = [
        ItemColumn('type', width=0),
        ItemColumn('id'),
        ItemColumn('duration_ms', type=int),
        ItemColumn('x', type=int),
        ItemColumn('y', type=int),
    ]


@DrawingSheet.property
def frames(sheet):
    return [r for r in sheet.rows if r.type == 'frame']


@DrawingSheet.property
def nFrames(sheet):
    return len(sheet.frames)


@DrawingSheet.api
def new_between_frame(sheet, fidx1, fidx2):
    f1 = f2 = None
    if not sheet.frames:
        name = '0'
    else:
        if 0 <= fidx1 < len(sheet.frames):
            f1 = sheet.frames[fidx1]
        if 0 <= fidx2 < len(sheet.frames):
            f2 = sheet.frames[fidx2]
        if f1 and f2:
            name = str(f1.id)+'-'+str(f2.id)
        elif f1:
            try: name = str(int(f1.id)+1)
            except ValueError: name = f'{f1.id}-post'
        elif f2:
            try: name = str(int(f2.id)-1)
            except ValueError: name = f'{f2.id}-pre'

    newf = sheet.newRow()
    newf.type = 'frame'
    newf.id = name
    newf.duration_ms = 100
    if f1:
        # insert frame just after the first frame in the actual rowset
        for i, r in enumerate(sheet.rows):
            if r is f1:
                vd.clearCaches()
                sheet.addRow(newf, index=i+1)
                break

        # copy all rows on frame1
        from copy import copy
        thisframerows = list(copy(r) for r in sheet.rows if f1.id in r.frame.split())
        for r in thisframerows:
            r.frame = newf.id
            sheet.addRow(r)
        return newf
    else:
        vd.clearCaches()
        return sheet.addRow(newf, index=0)
    vd.error('no existing frame ' + str(f1))


@Drawing.property
def currentFrame(dwg):
    if dwg.frames and 0 <= dwg.cursorFrameIndex < dwg.nFrames:
        return dwg.frames[dwg.cursorFrameIndex]
    return AttrDict()


@Drawing.property
def frameDesc(dwg):
    if not dwg.frames:
        return ''
    return f'Frame {dwg.currentFrame.id} {dwg.cursorFrameIndex}/{dwg.nFrames-1}'


@Drawing.api
def inFrame(dwg, r, frames):
    'Return True if *r* is an element that would be displayed (even if hidden or buried) in the given set of *frames*.'
    if r.type: return False  # frame or other non-element type
    if not r.frame: return True
    if not frames: return False
    return any(f.id in r.frame.split() for f in frames)


@Drawing.api
def stop_animation(dwg):
    dwg.autoplay_frames = []
    vd.timeouts_before_idle = 10
    vd.curses_timeout = 100
    vd.status('animation stopped')


@Drawing.api
def handle_autoplay(dwg, thisframe):
    'Handle animation playback logic and return the frame to display.'
    if not dwg.autoplay_frames:
        return thisframe

    now = time.time()
    vd.timeouts_before_idle = -1
    ft, f = dwg.autoplay_frames[0]
    thisframe = f
    if not ft:
        dwg.autoplay_frames[0][0] = now
    elif now-ft > f.duration_ms/1000:
        dwg.autoplay_frames.pop(0)
        if dwg.autoplay_frames:
            dwg.autoplay_frames[0][0] = now
            thisframe = dwg.autoplay_frames[0][1]
            vd.curses_timeout = thisframe.duration_ms
        else:
            # Reset to frame 0 by repopulating autoplay_frames
            dwg.autoplay_frames = [[0, f] for f in dwg.frames]
            dwg.cursorFrameIndex = 0
            dwg.autoplay_frames[0][0] = now
            thisframe = dwg.autoplay_frames[0][1]
            vd.curses_timeout = thisframe.duration_ms

    return thisframe


@Drawing.before
def checkCursor(dwg):
    dwg.cursorFrameIndex = max(min(dwg.cursorFrameIndex, len(dwg.frames)-1), 0)


Drawing.init('cursorFrameIndex', lambda: 0)
Drawing.init('autoplay_frames', list)

Drawing.class_options.disp_rstatus_fmt='{sheet.frameDesc} | {sheet.source.nRows} {sheet.rowtype}  {sheet.options.disp_selected_note}{sheet.source.nSelectedRows}'


Drawing.addCommand('F', 'open-frames', 'vd.push(FramesSheet(sheet, "frames", source=sheet, rows=sheet.frames, cursorRowIndex=sheet.cursorFrameIndex))')
Drawing.addCommand('[', 'prev-frame', 'sheet.cursorFrameIndex -= 1 if sheet.cursorFrameIndex > 0 else fail("first frame")')
Drawing.addCommand(']', 'next-frame', 'sheet.cursorFrameIndex += 1 if sheet.cursorFrameIndex < sheet.nFrames-1 else fail("last frame")')
Drawing.addCommand('g[', 'first-frame', 'sheet.cursorFrameIndex = 0')
Drawing.addCommand('g]', 'last-frame', 'sheet.cursorFrameIndex = sheet.nFrames-1')
Drawing.addCommand('z[', 'new-frame-before', 'sheet.new_between_frame(sheet.cursorFrameIndex-1, sheet.cursorFrameIndex)')
Drawing.addCommand('z]', 'new-frame-after', 'sheet.new_between_frame(sheet.cursorFrameIndex, sheet.cursorFrameIndex+1); sheet.cursorFrameIndex += 1')

Drawing.addCommand('gzs', 'select-all-this-frame', 'sheet.select(list(source.gatherBy(lambda r,f=currentFrame: r.frame == f.id)))')
Drawing.addCommand('gzu', 'unselect-all-this-frame', 'sheet.unselect(list(source.gatherBy(lambda r,f=currentFrame: r.frame == f.id)))')

Drawing.addCommand('r', 'reset-time', 'sheet.autoplay_frames.extend([[0, f] for f in sheet.frames])')
Drawing.addCommand('zr', 'stop-animation', 'sheet.stop_animation()', 'stop animation')

vd.addMenuItems('''
    DarkDraw > View > Frames sheet > open-frames
    DarkDraw > Animation > New frame > before > new-frame-before
    DarkDraw > Animation > New frame > after > new-frame-after
    DarkDraw > Animation > Go to frame > first > first-frame
    DarkDraw > Animation > Go to frame > last > last-frame
    DarkDraw > Animation > Go to frame > prev > prev-frame
    DarkDraw > Animation > Go to frame > next > next-frame
    DarkDraw > Animation > Start > reset-time
''')
