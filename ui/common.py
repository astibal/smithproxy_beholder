import sys

from PyQt5.QtGui import QColor

from util.fonts import load_font_prog

try:
    from PyQt5.Qsci import QsciScintilla, QsciLexerPython
    import pyperclip
except ImportError:
    print("This app requires Scintilla and pyperclip, optionally markdown for help.")
    print("Ubuntu: apt-get install python3-pyqt5.qsci python3-pyperclip")
    sys.exit(1)


def create_python_editor():
    lexer = QsciLexerPython()
    font = load_font_prog()
    font_bold = load_font_prog()
    font_bold.setBold(True)

    editor = QsciScintilla()

    lexer.setFont(font)
    lexer.setDefaultColor(QColor("#ffffff"))
    lexer.setPaper(QColor("#333333"))
    lexer.setColor(QColor("#888888"), QsciLexerPython.Comment)

    # Set font and color for keywords:
    lexer.setFont(font_bold, QsciLexerPython.Keyword)
    lexer.setColor(QColor("#a34000"), QsciLexerPython.Keyword)

    editor.setLexer(lexer)
    editor.setIndentationsUseTabs(False)
    editor.setTabWidth(4)
    editor.setAutoIndent(True)
    editor.setBraceMatching(QsciScintilla.SloppyBraceMatch)

    editor.setAutoCompletionSource(QsciScintilla.AcsAll)
    editor.setAutoCompletionCaseSensitivity(False)
    editor.setAutoCompletionReplaceWord(True)
    editor.setAutoCompletionThreshold(2)
    
    editor.setCallTipsVisible(10)
    editor.setCallTipsBackgroundColor(QColor("#f0f0f0")) 
    editor.setCallTipsForegroundColor(QColor("#404040")) 
    editor.setCallTipsHighlightColor(QColor("#808080"))
    
    editor.setFolding(QsciScintilla.PlainFoldStyle) 
    editor.setMarginType(3, QsciScintilla.SymbolMargin) 
    editor.setMarginWidth(3, "0") 
    editor.setMarginLineNumbers(1, True) 
    editor.setMarginWidth(1, "00000") 
    editor.setMarginsForegroundColor(QColor("#999999")) 
    editor.setMarginsBackgroundColor(QColor("#f0f0f0"))
    editor.setPaper(QColor("#f0f0f0"))

    bg = "#f9f9f2"
    lexer.setPaper(QColor(bg))
    editor.setMarginsBackgroundColor(QColor(bg))
    editor.setCaretLineBackgroundColor(QColor(bg))

    return editor
