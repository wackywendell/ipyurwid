#!/usr/bin/python

import urwid
txts = ['test{0} '.format(n) * 30 for n in range(30)]
txts = [urwid.Text(t) for t in txts]

edit = urwid.Edit()
lb = urwid.ListBox(txts)

pile = urwid.Pile([
    ('weight', 1, lb),
    ('flow', edit)
    ])

def unhandled(inpt):
    raise urwid.ExitMainLoop()
    
main = urwid.MainLoop(pile, unhandled_input=unhandled)

main.run()