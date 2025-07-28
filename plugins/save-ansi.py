from visidata import *

# Color names mapping to 256-color codes
color_names = {
    'black': 0, 'red': 1, 'green': 2, 'yellow': 3,
    'blue': 4, 'magenta': 5, 'cyan': 6, 'white': 7,
    'gray': 8, 'bright red': 9, 'bright green': 10,
    'bright yellow': 11, 'bright blue': 12, 'bright magenta': 13,
    'bright cyan': 14, 'bright white': 15,
}

def get_color_code(color):
    """Convert color name or number to 256-color code."""
    if color.isdigit():
        return int(color)
    color = color.lower()
    if color in color_names:
        return color_names[color]
    else:
        vd.warning(f'Unknown color {color} exported as black')
        return 0  # default to black

def parse_color(color_str):
    """Parse color string into attributes, foreground, and background."""
    parts = color_str.split(' on ')
    if len(parts) == 1:
        fg_part = parts[0]
        bg = None
    else:
        fg_part = parts[0]
        bg = parts[1].strip()

    words = fg_part.split()
    attributes = []
    color_candidates = []
    for word in words:
        if word in ['bold', 'italic', 'underline', 'reverse', 'dim', 'blink']:
            attributes.append(word)
        else:
            color_candidates.append(word)

    if color_candidates:
        for candidate in color_candidates:
            if candidate.isdigit():
                fg = candidate
                break
        else:
            fg = color_candidates[-1]
    else:
        fg = 'white'

    return attributes, fg, bg

def get_escape_codes(attributes, fg, bg):
    """Generate ANSI escape codes for attributes and colors."""
    codes = []
    attr_codes = {
        'bold': '1', 'dim': '2', 'italic': '3',
        'underline': '4', 'blink': '5', 'reverse': '7',
    }
    for attr in attributes:
        if attr in attr_codes:
            codes.append(attr_codes[attr])

    fg_code = get_color_code(fg)
    codes.append(f'38;5;{fg_code}')

    if bg:
        bg_code = get_color_code(bg)
        codes.append(f'48;5;{bg_code}')

    return '\033[' + ';'.join(codes) + 'm' if codes else ''

def export_frame(rows, x_col, y_col, text_col, color_col):
    """Export a single frame to ANSI text."""
    if not rows:
        return ''

    # Find max_x and max_y
    max_x = 0
    max_y = 0
    for row in rows:
        x = int(x_col.getValue(row))
        y = int(y_col.getValue(row))
        text = str(text_col.getValue(row))
        max_x = max(max_x, x + len(text) - 1)
        max_y = max(max_y, y)

    # Create grid
    grid = [[None] * (max_x + 1) for _ in range(max_y + 1)]

    # Place characters
    for row in rows:
        x = int(x_col.getValue(row))
        y = int(y_col.getValue(row))
        text = str(text_col.getValue(row))
        color_str = str(color_col.getValue(row))
        attributes, fg, bg = parse_color(color_str)
        for i, char in enumerate(text):
            grid[y][x + i] = (char, attributes, fg, bg)

    # Generate output
    output = ''
    for y in range(max_y + 1):
        line = ''
        prev_codes = None
        for x in range(max_x + 1):
            cell = grid[y][x]
            if cell:
                char, attributes, fg, bg = cell
                codes = get_escape_codes(attributes, fg, bg)
                if codes != prev_codes:
                    line += codes
                    prev_codes = codes
                line += char
            else:
                if prev_codes != '\033[0m':
                    line += '\033[0m'
                    prev_codes = '\033[0m'
                line += ' '
        line += '\033[0m'
        output += line + '\n'
    return output

def save_ansi(self):
    """Save the current sheet as an ANSI text file, exporting only rows with empty frame and type."""
    required_columns = ['x', 'y', 'text', 'color']
    columns_dict = {col.name: col for col in self.columns}
    for col_name in required_columns:
        if col_name not in columns_dict:
            vd.fail(f'Missing column: {col_name}')

    x_col = columns_dict['x']
    y_col = columns_dict['y']
    text_col = columns_dict['text']
    color_col = columns_dict['color']
    frame_col = columns_dict.get('frame', None)
    type_col = columns_dict.get('type', None)

    # Filter rows where both frame and type are empty
    filtered_rows = []
    for row in self.rows:
        frame_value = frame_col.getValue(row) if frame_col else None
        type_value = type_col.getValue(row) if type_col else None
        # Consider a value empty if it is None or an empty string
        if (frame_value is None or frame_value == '') and (type_value is None or type_value == ''):
            filtered_rows.append(row)

    if not filtered_rows:
        vd.warning('Drawing is animation; cannot export as ANSI.')
        return

    # Export filtered rows as a single frame
    output = export_frame(filtered_rows, x_col, y_col, text_col, color_col)

    output_filename = self.name + '.ans'
    with open(output_filename, 'w') as f:
        f.write(output)
    vd.status(f'Saved {len(filtered_rows)} rows to {output_filename}')

# Add the method to BaseSheet
BaseSheet.save_ansi = save_ansi

# Register the command
BaseSheet.addCommand(None, 'save-ansi', 'sheet.save_ansi()', helpstr='save current sheet as ANSI text (only rows with empty frame and type)')
