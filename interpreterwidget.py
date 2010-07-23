# coding: utf-8
"""Provides an urwid widget that can act like a terminal."""

import urwid
import pygments.lexers
import pygments.styles

from pywidget import *
from urwidpygments import UrwidFormatter


def recompose(text, attrlst):
    """For some reason, urwid.Text.get_text returns an object not
    suitable for use by urwid.Text.set_text. 'recompose' takes the
    two objects returned by get_text, and recomposes them for use by
    set_text. It is thus the inverse of urwid.decompose()."""
    markup = []
    for (attr, length) in attrlst:
        textpiece, text = text[:length], text[length:]
        markup.append((attr, textpiece))
    return markup


class interpreterwidget(urwid.Pile):
    """A widget that looks like an interpreter.

    Note that this is simply a widget, and has no extra functionality;
    it exists to organize the inner widgets."""
    def __init__(self, inputlines=4, caption='>>> '):
        # make inner widgets
        # first the input widgets
        # the input widgets are a 'captionwidget' for the prompt, next
        # to the inputwidget.
        # this means that the prompt is completely uneditable without
        # trying, and also takes care of indenting past the
        # prompt
        
        self.formatter = UrwidFormatter()
        self.lexer = pygments.lexers.get_lexer_by_name('python')
        
        self.inputbox = PromptPyEdit(multiline=True,lexer = self.lexer, formatter = self.formatter)
        self.inputwidget = urwid.Filler(self.inputbox, valign='top')
        
        # the completion box
        self.completionbox = TextGrid()
        
        # the 'upper' box, which can be switched to completions, help, etc.
        self.upperbox = Switcher(self.completionbox)
        
        # now the output widgets
        self.outputbox = urwid.Text('')    # Flow widget
        self.outputwidget = urwid.Filler(self.outputbox, valign='top')
                    # Box widget
        
        # now initialize as a pile
        urwid.Pile.__init__(self, [
            ('flow', self.upperbox),
            self.outputwidget,
            ('fixed', inputlines, self.inputwidget)]
        )
    
    def setinputcaption(self, caption):
        self.inputbox.set_prompt(caption)
        
    def setstyle(self, s):
        if isinstance(s, basestring):
            s = pygments.styles.get_style_by_name(s)
        self.formatter.style = s
    
    def addtooutput(self, markup):
        t = urwid.Text(markup)          # just to get it in a nice form
        newtxt, newattr = t.get_text()  # gets the attrs in a list form
        oldtxt, oldattr = self.outputbox.get_text()
        newtxt = oldtxt + newtxt
        newattr = oldattr + newattr
        markup = recompose(newtxt, newattr)
        return self.outputbox.set_text(markup)
        #return self.outputbox.set_text(('2', oldtxt + newtxt))

class fakeinterpreter(object):
    def __init__(self, widget):
        self.widget = widget
        self.widget.completionbox.set_text(['COMPLETION BOX','WIH COMPLETIONS','MORE COMPLETIONS'])
        
        allstyles = list(pygments.styles.get_all_styles())
        style = 'default'
        for s in ('monokai', 'native'):
            if s in allstyles:
                style = s
                break
        
#        self.widget.completionbox.set_text(s)
        widget.setstyle(s)
        
        self.n = 10
        
    def handleinput(self, inpt):
        txt = self.widget.inputbox.text
        if self.n <= 0 or txt.strip() == 'q' or txt.strip() == '':
            raise urwid.ExitMainLoop()
        
        self.n -= 1
        self.widget.inputbox.text =u''
        
        if txt.strip() == u's':
            if self.widget.upperbox.widget == self.widget.completionbox:
                self.widget.upperbox.widget = urwid.Text('Another widget!')
            else:
                self.widget.upperbox.widget = self.widget.completionbox
                #self.widget.upperbox.widget = urwid.Text('Another widget!')
            return True
        
        tkns = self.widget.lexer.get_tokens(txt)
        markup = list(self.widget.formatter.formatgenerator(tkns))
        
        #self.widget.addtooutput(('default','moretext:' + repr(inpt) + '\n'))
        self.widget.addtooutput(markup) 
        return True


if __name__ == "__main__":
    mainwin = interpreterwidget()
    interp = fakeinterpreter(mainwin)
    
    promptattr = urwid.AttrSpec('yellow, bold', 'default')
    
    mainwin.setinputcaption((promptattr, 'PROMPT> '))
    
    screen = urwid.raw_display.Screen()
    #screen.set_terminal_properties(colors=256)   # at least, try...
    #screen.reset_default_terminal_palette()      # get the normal colors
    loop = urwid.MainLoop(mainwin, screen=screen, 
                            unhandled_input=interp.handleinput)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
