import sys, subprocess
from subprocess import PIPE

import urwid
import pygments
from pygments import lexers, formatters, styles

l = lexers.get_lexer_by_name('python')
snames = styles.get_all_styles()
fs = [formatters.get_formatter_by_name('terminal256',style=s) for s in snames]

t = """def func(arg, key=val):
    try:
        print 4/0
    except Exception:
        return 2+2
"""

processedtxt = ''.join(pygments.highlight(t, l, f) for f in fs)
        

def run_pager(txt):
    proc = subprocess.Popen(['less', '-Rc'], stdin=PIPE)
    #proc = subprocess.Popen(['more', '-c'], stdin=PIPE)
    proc.communicate(txt)
    proc.wait()
    
class MainLoop(urwid.MainLoop):
    def unhandled_input(self, input):
        if input == 'q':
            raise urwid.ExitMainLoop()
        elif input == 'p':
            self.screen.stop()
            #run_pager('This is the pager!')
            run_pager(processedtxt)
            self.screen.start()
        else:
            self.txtwidget.set_text(input)
            self.draw_screen()
        return True

def main():
    #print "Running..."
    #run_pager(t)
    #print "Ran."
    #return
    
    s = urwid.raw_display.Screen()
    
    txtwidget = urwid.Text('Test!')
    widget = urwid.Filler(txtwidget)
    
    def handler(inpt):
        if inpt == 'q':
            raise urwid.ExitMainLoop()
        elif inpt == 'p':
            s.stop()
            #run_pager('This is the pager!')
            run_pager(processedtxt)
            s.start()
        else:
            txtwidget.set_text(inpt)
            s.draw_screen()
        return True
    
    loop = MainLoop(widget, screen=s)
    loop.txtwidget = txtwidget
    loop.run()

if __name__ == '__main__':
    main()