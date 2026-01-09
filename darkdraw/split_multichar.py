from darkdraw import Drawing, dispwidth
from copy import copy

### Split multi-character text objects into individual character objects.

@Drawing.api
def split_objects(sheet, rows):
    new_rows = []
    
    # Collect rows to split and their data
    rows_to_split = []
    for r in rows:
        if not r.text or r.type:
            continue
        if len(r.text) <= 1:
            continue
        rows_to_split.append(copy(r.__dict__))
    
    # Delete originals 
    sheet.source.deleteBy(lambda row: any(
        row.text == data['text'] and row.x == data['x'] and row.y == data['y'] 
        for data in rows_to_split
    ))
    
    # Create new rows from stored data
    for data in rows_to_split:
        x_offset = 0
        for char in data['text']:
            new_r = sheet.newRow()
            new_r.update(copy(data))
            new_r.text = char
            new_r.x = data['x'] + x_offset
            new_r.y = data['y']
            
            new_rows.append(new_r)
            sheet.source.addRow(new_r)
            
            x_offset += dispwidth(char)
    
    return len(new_rows)

Drawing.addCommand('/', 'split-cursor', 
    'n = split_objects(sheet.cursorRows); '
    'status(f"split into {n} objects")', 
    'split multi-character objects under cursor into individual characters')

Drawing.addCommand('g/', 'split-selected', 
    'n = split_objects(sheet.source.someSelectedRows); '
    'status(f"split into {n} objects")', 
    'split selected multi-character objects into individual characters')
