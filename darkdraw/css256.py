#!/usr/bin/env python3

def termcolor_to_rgb(n):
    if not n:
        return (255,255,255)
    colordict = dict(
            black=(0,0,0),
            blue=(114,159,207),
            green=(78,154,6),
            red=(204,0,0),
            cyan=(6,152,154),
            magenta=(255,0,255),
            brown=(196,160,0),
            white=(211,215,207),
            gray=(85,87,83),
            lightblue=(50,175,255),
            lightgreen=(138,226,52),
            lightaqua=(52,226,226),
            lightred=(239,41,41),
            lightpurple=(173,127,168),
            lightyellow=(252,233,79),
            brightwhite=(255,255,255),
    )
    if n in colordict:
        return colordict.get(n)
    n = int(n)
    if 0 <= n < 16:
        return list(colordict.values())[n]
    if 16 <= n < 232:
        n -= 16
        r,g,b = n//36,(n%36)//6,n%6
        ints = [0x00, 0x66, 0x88,0xbb,0xdd,0xff]
        return ints[r],ints[g],ints[b]
    else:
        n=list(range(8,255,10))[n-232]
        return n,n,n


def termcolor_to_css_color(n):
    n = str(n)
    if not n.isdigit():
        return n
    r,g,b = termcolor_to_rgb(n)
    return '#%02x%02x%02x' % (r,g,b)


for i in range(256):
    print(f'.fg{i} {{ color: {termcolor_to_css_color(i)}; }}')
    print(f'.bg{i} {{ background-color: {termcolor_to_css_color(i)}; }}')


for s in 'underline bold italic'.split():
    print(f'.{s} {{ font-style: {s}; }}')
