from darkdraw import Drawing, VisiData, vd

upgradeables = []
upgradeables += '''
┌ ╒ ┍ ╔ ┏
┌ ╓ ┎ ╔ ┏
└ ╘ ┕ ╚ ┗
└ ╙ ┖ ╚ ┗
┐ ╕ ┑ ╗ ┓
┐ ╖ ┒ ╗ ┓
┘ ╛ ┙ ╝ ┛
┘ ╜ ┚ ╝ ┛
├ ╞ ┝ ╠ ┣
├ ╟ ┠ ╠ ┣
┤ ╡ ┥ ╣ ┫
┤ ╢ ┨ ╣ ┫
┬ ╤ ┯ ╦ ┳
┬ ╥ ┰ ╦ ┳
┴ ╧ ┷ ╩ ┻
┴ ┸ ╨ ╩ ┻
┼ ╪ ┿ ╬ ╋
┼ ╫ ╂ ╬ ╋
─ ═ ━
│ ║ ┃

┞┟ ┠
┡┢ ┣
┦┧ ┨
┩┪ ┫
┭┮ ┯
┵┶ ┷
┱┲ ┳
┹┺ ┻
╁╀ ╂
┽┾ ┿
╄╃╅╆╇╈╉╊ ╋

- =
. :
! |
'''.splitlines()

upgradepath = {}
downgradepath = {}
for u in upgradeables[::-1]:
    v = u.split()
    for i, x in enumerate(v):
        for ch in x:
            if i+1 < len(v):
                upgradepath[ch] = v[i+1][0]
            if i-1 >= 0:
                downgradepath[ch] = v[i-1][0]


@VisiData.api
def downgrade(vd, s):
    return ''.join(downgradepath.get(ch, ch) for ch in s)

@VisiData.api
def upgrade(vd, s):
    return ''.join(upgradepath.get(ch, ch) for ch in s)


Drawing.addCommand('-', 'downgrade-cursor', 'for r in itercursor(): edit_text(downgrade(r.text), r)')
Drawing.addCommand('=', 'upgrade-cursor', 'for r in itercursor(): edit_text(upgrade(r.text), r)')
