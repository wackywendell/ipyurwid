import pydoc

import urwid, pygments

from interpreterwidget import InterpreterWidget, PagerScreen

class FakeInterpreter(object):
    def __init__(self, widget, screen):
        self.widget = widget
        self.widget.completionbox.set_text([
            'COMPLETION BOX',
            'Currently',
            'Not hooked up',
            'but',
            'fully',
            'functional',
            'as a',
            'widget',
            'these',
            'words',
            'show the',
            'grid layout'
        ])
        
        self.screen = screen
        
        allstyles = list(pygments.styles.get_all_styles())
        style = 'default'
        for s in ('monokai', 'native'):
            if s in allstyles:
                style = s
                break
        
#        self.widget.completionbox.set_text(s)
        widget.set_style(s)
        
        self.widget.upperbox.widget = urwid.Text(self.usagetext)
        
    usagetext = '''\
This is a demo of this widget.
Type python code to show text highlighting.
Hit enter to see it enter the interpreter. This is a fake interpreter, so code
is not processed, merely displayed as output.

Others:
CTRL-D : exit
CTRL-P : show the pager (with prearranged text from pydoc).
CTRL-O : Show help for entered text (simply runs pydoc, then uses pager)
CTRL-W : Switch widget at the top'''
    def handle_input(self, inpt):
        if inpt == 'enter':
            return self.accept_input()
        elif inpt == 'ctrl d':
            raise urwid.ExitMainLoop()
        elif inpt == 'ctrl p':
            self.screen.page(pydoc.render_doc('pydoc'))
            return True
        elif inpt == 'ctrl o':
            txt = self.widget.inputbox.text.strip()
            try:
                fulltxt = pydoc.render_doc(str(txt))
            except ImportError:
                fulltxt = 'No documentation found for ' + repr(txt)
            self.screen.page(fulltxt)
            return True
        if inpt == 'ctrl w': # widget switch
            if self.widget.upperbox.widget == self.widget.completionbox:
                self.widget.upperbox.widget = urwid.Text(self.usagetext)
            else:
                self.widget.upperbox.widget = self.widget.completionbox
                #self.widget.upperbox.widget = urwid.Text('Another widget!')
            return True
        else:
            self.widget.upperbox.widget = urwid.Text(inpt)
            return True
    
    def accept_input(self):
        txt = self.widget.inputbox.text
        if txt.strip() == 'quit':
            raise urwid.ExitMainLoop()
        
        self.widget.inputbox.text =u''
        if txt.strip() == u'':
            return True
        
        self.widget.inputbox.text =u''
        
        tkns = self.widget.lexer.get_tokens(txt.strip())
        markup = list(self.widget.formatter.formatgenerator(tkns))
        
        #self.widget.add_to_output(('default','moretext:' + repr(markup) + '\n'))
        self.widget.add_to_output(markup) 
        return True

def main():
    mainwin = InterpreterWidget()
    
    screen = PagerScreen()
    interp = FakeInterpreter(mainwin, screen)
    
    promptattr = urwid.AttrSpec('yellow, bold', 'default')
    
    mainwin.set_input_caption((promptattr, 'PROMPT> '))
    
    #screen.set_terminal_properties(colors=256)   # at least, try...
    #screen.reset_default_terminal_palette()      # get the normal colors
    loop = urwid.MainLoop(mainwin, screen=screen, 
                            unhandled_input=interp.handle_input)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
    exit()
    
    # profiling?
    import hotshot
    prof = hotshot.Profile('interp text')
    prof.runcall(main)
    #import cProfile
    
