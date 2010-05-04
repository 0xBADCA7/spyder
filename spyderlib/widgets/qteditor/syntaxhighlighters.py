# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Editor widget syntax highlighters based on PyQt4.QtGui.QSyntaxHighlighter
Syntax highlighting rules are inspired from idlelib
"""

import sys, re, keyword, __builtin__

from PyQt4.QtGui import (QColor, QApplication, QFont, QSyntaxHighlighter,
                         QCursor, QTextCharFormat)
from PyQt4.QtCore import Qt

# For debugging purpose:
STDOUT = sys.stdout


#===============================================================================
# Python syntax highlighter
#===============================================================================
def any(name, alternates):
    "Return a named group pattern matching list of alternates."
    return "(?P<%s>" % name + "|".join(alternates) + ")"

def make_python_patterns():
    "Strongly inspired from idlelib.ColorDelegator.make_pat"
    kw = r"\b" + any("KEYWORD", keyword.kwlist) + r"\b"
    builtinlist = [str(name) for name in dir(__builtin__)
                                        if not name.startswith('_')]
    builtin = r"([^.'\"\\#]\b|^)" + any("BUILTIN", builtinlist) + r"\b"
    comment = any("COMMENT", [r"#[^\n]*"])
    instance = any("INSTANCE", [r"\bself\b"])
    number = any("NUMBER",
                 [r"\b[+-]?[0-9]+[lL]?\b",
                  r"\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b",
                  r"\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"])
    ml_sq3string = r"(\b[rRuU])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(?!''')[^\n]*"
    ml_dq3string = r'(\b[rRuU])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(?!""")[^\n]*'
    multiline_string = any("ML_STRING", [ml_sq3string, ml_dq3string])
    sqstring = r"(\b[rRuU])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
    dqstring = r'(\b[rRuU])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
    sq3string = r"(\b[rRuU])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
    dq3string = r'(\b[rRuU])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
    string = any("STRING", [sq3string, dq3string, sqstring, dqstring])
    return instance + "|" + kw + "|" + builtin + "|" + comment + "|" + \
           multiline_string + "|" + string + "|" + number + "|" + \
           any("SYNC", [r"\n"])

class PythonSH(QSyntaxHighlighter):
    """Python Syntax Highlighter"""
    # Syntax highlighting rules:
    PROG = re.compile(make_python_patterns(), re.S)
    IDPROG = re.compile(r"\s+(\w+)", re.S)
    ASPROG = re.compile(r".*?\b(as)\b")
    # Syntax highlighting states (from one text block to another):
    NORMAL = 0
    INSIDE_STRING = 1
    # Syntax highlighting color schemes:
    COLORS = {
              'IDLE':
              (#  Name          Color    Bold   Italic
               ("NORMAL",     "#000000", False, False),
               ("KEYWORD",    "#ff7700", True,  False),
               ("BUILTIN",    "#900090", False, False),
               ("DEFINITION", "#0000ff", False, False),
               ("COMMENT",    "#dd0000", False, True),
               ("STRING",     "#00aa00", False, False),
               ("NUMBER",     "#924900", False, False),
               ("INSTANCE",   "#777777", True,  True),
               ),
              'Pydev':
              (#  Name          Color    Bold   Italic
               ("NORMAL",     "#000000", False, False),
               ("KEYWORD",    "#0000FF", False, False),
               ("BUILTIN",    "#900090", False, False),
               ("DEFINITION", "#000000", True,  False),
               ("COMMENT",    "#C0C0C0", False, False),
               ("STRING",     "#00AA00", False, True),
               ("NUMBER",     "#800000", False, False),
               ("INSTANCE",   "#000000", False, True),
               ),
              'Scintilla':
              (#  Name          Color    Bold   Italic
               ("NORMAL",     "#000000", False, False),
               ("KEYWORD",    "#00007F", True,  False),
               ("BUILTIN",    "#000000", False, False),
               ("DEFINITION", "#007F7F", True,  False),
               ("COMMENT",    "#007F00", False, False),
               ("STRING",     "#7F007F", False, False),
               ("NUMBER",     "#007F7F", False, False),
               ("INSTANCE",   "#000000", False, True),
               ),
              }
    def __init__(self, parent, font=None, color_scheme=None):
        super(PythonSH, self).__init__(parent)
        
        if color_scheme is None:
            color_scheme = 'Pydev'
        self.color_scheme = color_scheme

        self.formats = None
        self.setup_formats(font)

    def setup_formats(self, font=None):
        base_format = QTextCharFormat()
        if font is not None:
            base_format.setFont(font)
        self.formats = {}
        for name, color, bold, italic in self.COLORS[self.color_scheme]:
            format = QTextCharFormat(base_format)
            format.setForeground(QColor(color))
            if bold:
                format.setFontWeight(QFont.Bold)
            format.setFontItalic(italic)
            self.formats[name] = format
            if name == "STRING":
                self.formats["ML_STRING"] = format

    def highlightBlock(self, text):
        text_length = text.length()
        previous_state = self.previousBlockState()

        current_format = self.formats["NORMAL"]
        inside_string = previous_state == self.INSIDE_STRING
        if inside_string:
            current_format = self.formats["STRING"]
            last_state = self.INSIDE_STRING
        else:
            last_state = None
        self.setFormat(0, text_length, current_format)
            
        chars = text
        m = self.PROG.search(chars)
        index = 0
        while m:
            for key, value in m.groupdict().items():
                if value:
                    a, b = m.span(key)
                    index += b-a
                    if inside_string:
                        self.setFormat(a, b-a, self.formats["STRING"])
                    else:
                        self.setFormat(a, b-a, self.formats[key])
                        if value in ("def", "class"):
                            m1 = self.IDPROG.match(chars, b)
                            if m1:
                                a, b = m1.span(1)
                                self.setFormat(a, b-a,
                                               self.formats["DEFINITION"])
                        elif value == "import":
                            # color all the "as" words on same line, except
                            # if in a comment; cheap approximation to the
                            # truth
                            if '#' in chars:
                                endpos = chars.index('#')
                            else:
                                endpos = len(chars)
                            while True:
                                m1 = self.ASPROG.match(chars, b, endpos)
                                if not m1:
                                    break
                                a, b = m1.span(1)
                                self.setFormat(a, b-a, self.formats["KEYWORD"])
                    if key == "ML_STRING":
                        inside_string = not inside_string
                        if inside_string:
                            current_format = self.formats["STRING"]
                            last_state = self.INSIDE_STRING
                        else:
                            current_format = self.formats["NORMAL"]
                            last_state = self.NORMAL
                    
            m = self.PROG.search(chars, m.end())

        if last_state is None:
            last_state = self.NORMAL
        self.setCurrentBlockState(last_state)

    def rehighlight(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QSyntaxHighlighter.rehighlight(self)
        QApplication.restoreOverrideCursor()

