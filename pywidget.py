# encoding: UTF-8
import pygments, pygments.lexers, pygments.formatters

import subprocess

import urwid
import urwid.widget as widget
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


class PythonEdit(widget.Edit): # flow
    """An editbox that colorizes python code.
    A FLOW widget."""
    def __init__(self, edit_text="", multiline=True,
            align='left', wrap='space', allow_tab=True,
            edit_pos=None, layout=None, lexer=None, formatter=None):
                
        if lexer is not None:
            self.lexer = lexer
        else:
            self.lexer = pygments.lexers.get_lexer_by_name('python')
        
        if formatter is not None:
            self.formatter = formatter
        else:
            self.formatter = UrwidFormatter()
            
        # note: captions not allowed
        widget.Edit.__init__(self, '', edit_text, multiline, align,
            wrap, allow_tab, edit_pos, layout)
        
        if edit_text:
            self.colorize()
        
        self.enterpressed=False
        
    def handlekey(self, size, key):
        """Extra magic for a python editor"""
        # deal with double enter - return it
        if key == 'enter' and self.multiline and not self.enterpressed:
            self.enterpressed = True
            return urwid.Edit.keypress(self, size, key)
            
        elif key == 'enter' and self.multiline and self.enterpressed:
            return key
        else:
            self.enterpressed = False
        
        return widget.Edit.keypress(self, size, key)
    
    def keypress(self, size, key):
        """Handles colorpress"""
        retval = self.handlekey(size, key)
        self.colorize()
        return retval
    
    @property
    def markup(self):
        return self.get_text()

    def colorize(self):
        text = self.edit_text
        assert hasattr(self, 'formatter')
        assert hasattr(self, 'lexer')
        tkns = self.lexer.get_tokens(text)
        markup = list(self.formatter.formatgenerator(tkns))
        widget.Text.set_text(self, markup)

class PromptPyEdit(widget.WidgetWrap):
    """A widget that adds a prompt to the PythonEdit widget.
    A FLOW widget."""
    def __init__(self, prompt="", edit_text="", multiline=True,
            align='left', wrap='space', allow_tab=True,
            edit_pos=None, layout=None, lexer=None, formatter=None):
        
        self.promptbox = widget.Text('')
        self.editbox = PythonEdit(edit_text, multiline, align,
            wrap, allow_tab, edit_pos, layout, lexer, formatter)
        self.columns = urwid.Columns([self.promptbox, self.editbox])
        self.set_prompt(prompt)
        widget.WidgetWrap.__init__(self, self.columns)
    
    @property
    def text(self):
        return self.editbox.edit_text
    
    @text.setter
    def text(self, text):
        self.editbox.edit_text = text
    
    @property
    def markup(self):
        return self.editbox.markup
    
    @property
    def prompt(self):
        """The text for the Python input. Not settable for the same reasons
        as Text.text: this property returns a string, but markup can be
        used for setting the prompt."""
        return self.promptbox.text
    
    def set_prompt(self, prompt):
        self.promptbox.set_text(prompt)
        txt = self.promptbox.text
        
        self.columns.column_types[0] = ('fixed', len(txt)   )
    
    def get_prompt(self):
        return self.promptbox.get_text()
    
    def render(self, *args, **kwargs):
        # if the promptbox is empty, bypass the 'columns' part and just render
        # the editbox. This is necessary as the Columns widget cannot handle 
        # empty widgets
        if self.prompt:
            return self.columns.render(*args, **kwargs)
        else:
            return self.editbox.render(*args, **kwargs)

class TextGrid(widget.WidgetWrap):
    """Displays a list of strings as a grid, allowing only a given width."""
    def __init__(self, texts=None, width = 15):
        """
        texts -- list of strings, unicode objects, or markup to be used in the 
                 cells. May be markup, but may not include newlines."""
        grid = urwid.GridFlow([], width, 1,0,'left')
        widget.WidgetWrap.__init__(self, grid)
        if texts is not None:
            self.set_text(texts)
    
    def set_text(self, cells):
        """Takes a list of str/unicode/markup to be used as the cells of the 
        grid.
        
        NOTE: Newlines are NOT SUPPORTED, and not all that well handled 
        (they raise a NotImplementedError)."""
        cells = [widget.Text(markup, align='left', wrap='clip') for markup in cells]
        for cell in cells:
            if '\n' in cell.text:
                raise NotImplementedError(
                    'TextGrid can not handle Text with newlines.')
        self._w.cells[:] = cells
        if cells:
            self._w.focus_cell = cells[0]
        self._w._cache_maxcol = None
        self._w._invalidate()
        self._invalidate()
        
    @property
    def cellwidth(self):
        return self._w.cell_width
    
    @cellwidth.setter
    def cellwidth(self, width):
        self._w.cell_width = width
        self._w._cache_maxcol = None # hack to invalidate caches
    
    @cellwidth.deleter
    def cellwidth(self):
        self._w.cell_width = 15
        self._w._cache_maxcol = None # hack to invalidate caches

class Switcher(widget.WidgetWrap):
    def __init__(self, firstwidget=None):
        if firstwidget is None:
            firstwidget=urwid.Text('')
            self._blank=True
        else:
            self._blank=False
        
        widget.WidgetWrap.__init__(self, firstwidget)
    
    @property
    def widget(self):
        if self._blank:
            return None
        return self._w
    
    @widget.setter
    def widget(self, newwidget):
        if newwidget is None:
            del self.widget
        else:
            self._w = newwidget
            self._blank = False
        self._invalidate()
    
    @widget.deleter
    def widget(self):
        self._w = urwid.Text('')
        self.blank = True
        self._invalidate()

class UpperBox(widget.WidgetWrap):
    def __init__(self, firstwidget=None):
        self._divider = urwid.Divider(u'─')
        self._switcher = Switcher(firstwidget)
        mywidget = urwid.Pile([self._switcher, self._divider])
        widget.WidgetWrap.__init__(self, mywidget)
    @property
    def widget(self):
        return self._switcher.widget
    
    @widget.setter
    def widget(self, newwidget):
        self._switcher.widget = newwidget
        self._invalidate()
    
    @widget.deleter
    def widget(self):
        del self._switcher.widget
        self._invalidate()

class OutputBox(widget.WidgetWrap):
    def __init__(self, remember=1000, jumptobottom=True): #, lexer=None, formatter=None):
        self.remember = remember
        #self.lexer=lexer
        #self.formatter=formatter
        self.list = urwid.SimpleListWalker([])
        self.jumptobottom = jumptobottom
        mywidget = urwid.ListBox(self.list)
        widget.WidgetWrap.__init__(self, mywidget)
    
    @property
    def jumptobottom(self):
        return self._jumptobottom
    
    @jumptobottom.setter
    def jumptobottom(self, val):
        self._jumptobottom = bool(val)
        if len(self.list) > 0:
            self.list.set_focus(len(self.list))
        
    def add_stdout(self, markup):
        t=urwid.Text(markup)
        txt, attrs = t.get_text()
        if len(txt) > 0 and txt[-1] == u'\n':
            txt = txt[:-1]
            t.set_text(recompose(txt, attrs))
        self.list.append(t)
        self.list[:] = self.list[-self.remember:]
        if self.jumptobottom:
            self.list.set_focus(len(self.list))
    
    def atbottom(self, size):
        return 'bottom' in self._w.ends_visible(size)
    
class PagerScreen(urwid.raw_display.Screen):
    """Derives from urwid.raw_display.Screen, and adds a function to run text
    through a pager."""
    def page(self, txt):
        """Turn off urwid, run a pager, and then resume.
        Text is handed directly to the pager, so any markup needs to be turned
        into basic terminal escapes."""
        
        started = self._started
        if started:
            self.stop()
        proc = subprocess.Popen(['less', '-Rc'], stdin=subprocess.PIPE)
        #proc = subprocess.Popen(['more', '-c'], stdin=PIPE)
        try:
            proc.communicate(txt)
        except IOError:
            pass
        proc.wait()
        self.start()
