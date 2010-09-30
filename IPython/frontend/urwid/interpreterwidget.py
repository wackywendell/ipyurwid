# coding: utf-8
"""Provides an urwid widget that can act like a terminal."""

import urwid
import pygments.lexers
import pygments.styles
import pygments
import pydoc

from pywidget import *
from urwidpygments import UrwidFormatter


class InterpreterWidget(urwid.Pile):
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
        self.lexer = pygments.lexers.get_lexer_by_name('python', stripall='True', ensurenl='False')
        self.errlexer = pygments.lexers.get_lexer_by_name('pytb', stripall='True', ensurenl='False')

        self.inputbox = PromptPyEdit(multiline=True,lexer = self.lexer, formatter = self.formatter)
        self.inputwidget = urwid.Filler(self.inputbox, valign='top')
        
        # the completion box
        self.completionbox = TextGrid()
        
        # the 'upper' box, which can be switched to completions, help, etc.
        self.upperbox = UpperBox(self.completionbox)
        
        # now the output widgets
        self.outputbox = OutputBox()    # Box widget
        self.outputwidget = self.outputbox
        #self.outputwidget = urwid.Filler(self.outputbox, valign='top')
                    # Box widget
        
        # now initialize as a pile
        urwid.Pile.__init__(self, [
            ('flow', self.upperbox),
            self.outputwidget,
            ('fixed', inputlines, self.inputwidget)]
        )
        self.set_focus(self.inputwidget)
    
    def set_input_caption(self, caption):
        self.inputbox.set_prompt(caption)
    
    def highlight(self, txt):
        tkns = self.lexer.get_tokens(txt)
        return list(self.formatter.formatgenerator(tkns))

    def highlight_err(self, txt):
        tkns = self.errlexer.get_tokens(txt)
        return list(self.formatter.formatgenerator(tkns))

    @property
    def input_text(self):
        return self.inputbox.text
    
    @input_text.setter
    def input_text(self, newtxt):
        self.inputbox.text = u''
        
    def set_style(self, s):
        if isinstance(s, basestring):
            s = pygments.styles.get_style_by_name(s)
        self.formatter.style = s
    
    def add_to_output(self, markup):
        self.outputbox.add_stdout(markup)
        return
        
    def _get_widget_size(self, widget, selfsize):
        item_rows = None
        if len(selfsize)==2: # Box widget
            item_rows = self.get_item_rows( selfsize, focus=True )
        i = self.widget_list.index(widget)
        return self.get_item_size(selfsize,i,True,item_rows)
    
    def _passkey(self, widget, size, key):
        """Pass the key along to an inner widget."""
        tsize = self._get_widget_size(widget, size)
        key = widget.keypress( tsize, key )
        return key
    
    def keypress(self, size, key):
        """We do not want the normal urwid.Pile keypress stuff to happen..."""
        # let the focus item use the key, if it can...
        if (self.focus_item.selectable() and 
                self.focus_item is not self.outputwidget):
            key = self._passkey(self.focus_item, size, key)
        
        # try it on the outputbox
    
        origkey = key
        if key in ('up','page up', 'home'):
            self.outputbox.jumptobottom = False
            key = None
        key = self._passkey(self.outputwidget, size, origkey)
        tsize = self._get_widget_size(self.outputwidget, size)
        if (origkey in ('down', 'page down', 'end')
                and self.outputbox.atbottom(tsize)):
            self.outputbox.jumptobottom = True
            key = None
        
        if key == 'ctrl k':
            # switch focus widget
            if self.focus_item is self.outputwidget:
                self.set_focus(self.inputwidget)
            else:
                self.set_focus(self.outputwidget)
            return
        return key
