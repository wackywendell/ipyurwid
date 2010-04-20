"""Provides an urwid widget that can act like a terminal."""

import urwid
import pygments.lexers, pygments.styles
from urwidpygments import UrwidFormatter

def recompose(text, attrlst):
    """For some reason, urwid.Text.get_text returns an object not 
    suitable for use by urwid.Text.set_text. 'recompose' takes the 
    two objects returned by get_text, and recomposes them for use by 
    set_text. It is thus the inverse of urwid.decompose().
    
    """
    markup = []
    for (attr, length) in attrlst:
        textpiece, text = text[:length], text[length:]
        markup.append((attr, textpiece))
    return markup

class interpreterwidget(urwid.Pile):
    """A widget that looks like an interpreter.
    
    Note that this is simply a widget, and has no extra functionality;
    it exists to organize the inner widgets."""
    def __init__(self, inputlines = 4, caption = '>>> '):
        # make inner widgets
        # first the input widgets
        # the input widgets are a 'captionwidget' for the prompt, next
        # to the inputwidget.
        # this means that the prompt is completely uneditable without
        # trying, and also takes care of indenting past the
        # prompt
        self.captionwidget = urwid.Text(caption)
        self.inputbox = urwid.Edit()
        self.inputcols = urwid.Columns(( # Flow widget (from inputbox)
            ('fixed',len(caption),self.captionwidget), 
            self.inputbox
        ))
        self.inputwidget = urwid.Filler(self.inputcols,valign='top')
        
        # the completion box
        self.completionbox = urwid.Text('')
        
        # now the output widgets
        self.outputbox = urwid.Text('') # F
        self.outputwidget = urwid.Filler(self.outputbox,valign='top') # B
        
        # now initialize as a pile
        urwid.Pile.__init__(self, [
            ('flow',self.completionbox),
            self.outputwidget,
            ('fixed', inputlines, self.inputwidget)]
        )
    
    def setinputcaption(self, caption):
        t = urwid.Text(caption) # just to get it in a nice form
        captiontxt, attr = t.get_text() # this allows 'caption' to
                                        # be urwid markup
        self.inputcols.column_types[0] = ('fixed', len(captiontxt))
        self.captionwidget.set_text(caption)
    
    def addtooutput(self, markup):
        t = urwid.Text(markup) # just to get it in a nice form
        newtxt, newattr = t.get_text() # gets the attrs in a list form
        oldtxt, oldattr = self.outputbox.get_text()
        newtxt = oldtxt + newtxt
        newattr = oldattr + newattr
        markup = recompose(newtxt, newattr)
        return self.outputbox.set_text(markup)
        #return self.outputbox.set_text(('2', oldtxt + newtxt))

class fakeinterpreter(object):
    def __init__(self, widget):
        self.widget = widget
        
        allstyles = list(pygments.styles.get_all_styles())
        style = 'default'
        for s in ('monokai', 'native'):
            if s in allstyles:
                style = s
        self.formatter = UrwidFormatter(style=s)
        self.lexer = pygments.lexers.get_lexer_by_name('python')
        self.widget.completionbox.set_text('COMPLETION BOX\nWIH COMPLETIONS')
        urwid.connect_signal(self.widget.inputbox, 'change', self.colorizeinput)
        self.n = 10
    def colorizeinput(self, box, txt):
        pass
        # This is actually not possible - urwid Edit widgets can not
        # do colors, unfortunately.
        
        # Here is the code it should be...
        #tkns = self.lexer.get_tokens(txt)
        #markup = list(self.formatter.formatgenerator(tkns))
        #self.widget.inputbox.set_edit_text(markup)
        
    def handleinput(self, inpt):
        
        txt = self.widget.inputbox.edit_text
        if self.n <= 0 or txt.strip() == 'q':
            raise urwid.ExitMainLoop()
        self.n -= 1
        self.widget.inputbox.edit_text = ''
        tkns = self.lexer.get_tokens(txt)
        markup = list(self.formatter.formatgenerator(tkns))
        
        #self.widget.addtooutput(('default','moretext:' + repr(inpt) + '\n'))
        self.widget.addtooutput(markup) 

if __name__ == "__main__":
    mainwin = interpreterwidget()
    mainwin.setinputcaption('PROMPT> ')
    interp = fakeinterpreter(mainwin)
    
    screen = urwid.raw_display.Screen()
    screen.set_terminal_properties(colors=256) # at least, try...
    screen.reset_default_terminal_palette() # get the normal colors
    loop = urwid.MainLoop(mainwin, screen=screen, unhandled_input=interp.handleinput)
    loop.run()