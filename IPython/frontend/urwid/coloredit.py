import urwid
import urwid.widget as widget

class ColorEdit(widget.Edit):
    """A class that allows for colorized text."""
    def __init__(self, caption="", edit_text="", multiline=False,
            align='left', wrap='space', allow_tab=False,
            edit_pos=None, layout=None):
        widget.Edit.__init__(self, caption, edit_text, multiline, align,
            wrap, allow_tab, edit_pos, layout)
        
        self._colorize()
    
    def keypress(self, size, key):
        widget.Edit.keypress(self, size, key)
        self._colorize()
    
    def _colorize(self):
        widget.Text.set_text(self, self.colorize())
    
    def colorize(self):
        """Overrideable method that should return markup to be used as the text."""
        return self.edit_text
    
    
    