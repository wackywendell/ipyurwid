""" Utilities for processing ANSI escape codes and special ASCII characters.
"""
#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Standard library imports
from collections import namedtuple
import re

# System library imports
from PyQt4 import QtCore, QtGui

#-----------------------------------------------------------------------------
# Constants and datatypes
#-----------------------------------------------------------------------------

# An action for erase requests (ED and EL commands).
EraseAction = namedtuple('EraseAction', ['action', 'area', 'erase_to'])

# An action for cursor move requests (CUU, CUD, CUF, CUB, CNL, CPL, CHA, CUP,
# and HVP commands).
# FIXME: Not implemented in AnsiCodeProcessor.
MoveAction = namedtuple('MoveAction', ['action', 'dir', 'unit', 'count'])

# An action for scroll requests (SU and ST) and form feeds.
ScrollAction = namedtuple('ScrollAction', ['action', 'dir', 'unit', 'count'])

#-----------------------------------------------------------------------------
# Classes
#-----------------------------------------------------------------------------

class AnsiCodeProcessor(object):
    """ Translates special ASCII characters and ANSI escape codes into readable
        attributes.
    """

    # Whether to increase intensity or set boldness for SGR code 1.
    # (Different terminals handle this in different ways.)
    bold_text_enabled = False    

    # Protected class variables.
    _ansi_commands = 'ABCDEFGHJKSTfmnsu'
    _ansi_pattern = re.compile('\x01?\x1b\[(.*?)([%s])\x02?' % _ansi_commands)
    _special_pattern = re.compile('([\f])')

    #---------------------------------------------------------------------------
    # AnsiCodeProcessor interface
    #---------------------------------------------------------------------------

    def __init__(self):
        self.actions = []
        self.reset_sgr()

    def reset_sgr(self):
        """ Reset graphics attributs to their default values.
        """
        self.intensity = 0
        self.italic = False
        self.bold = False
        self.underline = False
        self.foreground_color = None
        self.background_color = None

    def split_string(self, string):
        """ Yields substrings for which the same escape code applies.
        """
        self.actions = []
        start = 0

        for match in self._ansi_pattern.finditer(string):
            raw = string[start:match.start()]
            substring = self._special_pattern.sub(self._replace_special, raw)
            if substring or self.actions:
                yield substring
            start = match.end()

            self.actions = []
            try:
                params = []
                for param in match.group(1).split(';'):
                    if param:
                        params.append(int(param))
            except ValueError:
                # Silently discard badly formed escape codes.
                pass
            else:
                self.set_csi_code(match.group(2), params)

        raw = string[start:]
        substring = self._special_pattern.sub(self._replace_special, raw)
        if substring or self.actions:
            yield substring

    def set_csi_code(self, command, params=[]):
        """ Set attributes based on CSI (Control Sequence Introducer) code.

        Parameters
        ----------
        command : str
            The code identifier, i.e. the final character in the sequence.
        
        params : sequence of integers, optional
            The parameter codes for the command.
        """
        if command == 'm':   # SGR - Select Graphic Rendition
            if params:
                for code in params:
                    self.set_sgr_code(code)
            else:
                self.set_sgr_code(0)

        elif (command == 'J' or # ED - Erase Data
              command == 'K'):  # EL - Erase in Line
            code = params[0] if params else 0
            if 0 <= code <= 2:
                area = 'screen' if command == 'J' else 'line'
                if code == 0:
                    erase_to = 'end'
                elif code == 1:
                    erase_to = 'start'
                elif code == 2:
                    erase_to = 'all'
                self.actions.append(EraseAction('erase', area, erase_to))

        elif (command == 'S' or # SU - Scroll Up
              command == 'T'):  # SD - Scroll Down
            dir = 'up' if command == 'S' else 'down'
            count = params[0] if params else 1
            self.actions.append(ScrollAction('scroll', dir, 'line', count))
        
    def set_sgr_code(self, code):
        """ Set attributes based on SGR (Select Graphic Rendition) code.
        """
        if code == 0:
            self.reset_sgr()
        elif code == 1:
            if self.bold_text_enabled:
                self.bold = True
            else:
                self.intensity = 1
        elif code == 2:
            self.intensity = 0
        elif code == 3:
            self.italic = True
        elif code == 4:
            self.underline = True
        elif code == 22:
            self.intensity = 0
            self.bold = False
        elif code == 23:
            self.italic = False
        elif code == 24:
            self.underline = False
        elif code >= 30 and code <= 37:
            self.foreground_color = code - 30
        elif code == 39:
            self.foreground_color = None
        elif code >= 40 and code <= 47:
            self.background_color = code - 40
        elif code == 49:
            self.background_color = None

    #---------------------------------------------------------------------------
    # Protected interface
    #---------------------------------------------------------------------------

    def _replace_special(self, match):
        special = match.group(1)
        if special == '\f':
            self.actions.append(ScrollAction('scroll', 'down', 'page', 1))
        return ''
        

class QtAnsiCodeProcessor(AnsiCodeProcessor):
    """ Translates ANSI escape codes into QTextCharFormats.
    """

    # A map from color codes to RGB colors.
    default_map = (# Normal,      Bright/Light    ANSI color code
                   ('black',      'grey'),        # 0: black
                   ('darkred',    'red'),         # 1: red
                   ('darkgreen',  'lime'),        # 2: green
                   ('brown',      'yellow'),      # 3: yellow
                   ('darkblue',   'deepskyblue'), # 4: blue
                   ('darkviolet', 'magenta'),     # 5: magenta
                   ('steelblue',  'cyan'),        # 6: cyan
                   ('grey',       'white'))       # 7: white

    def __init__(self):
        super(QtAnsiCodeProcessor, self).__init__()
        self.color_map = self.default_map
    
    def get_format(self):
        """ Returns a QTextCharFormat that encodes the current style attributes.
        """
        format = QtGui.QTextCharFormat()

        # Set foreground color
        if self.foreground_color is not None:
            color = self.color_map[self.foreground_color][self.intensity]
            format.setForeground(QtGui.QColor(color))

        # Set background color
        if self.background_color is not None:
            color = self.color_map[self.background_color][self.intensity]
            format.setBackground(QtGui.QColor(color))

        # Set font weight/style options
        if self.bold:
            format.setFontWeight(QtGui.QFont.Bold)
        else:
            format.setFontWeight(QtGui.QFont.Normal)
        format.setFontItalic(self.italic)
        format.setFontUnderline(self.underline)

        return format

    def set_background_color(self, color):
        """ Given a background color (a QColor), attempt to set a color map
            that will be aesthetically pleasing.
        """
        if color.value() < 127:
            # Colors appropriate for a terminal with a dark background.
            self.color_map = self.default_map

        else:
            # Colors appropriate for a terminal with a light background. For 
            # now, only use non-bright colors...
            self.color_map = [ (pair[0], pair[0]) for pair in self.default_map ]

            # ...and replace white with black.
            self.color_map[7] = ('black', 'black')
