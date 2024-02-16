import logging
import re

from PyQt5.QtGui import QFont, QFontDatabase

def load_font_prog() -> QFont:
    preferred_fonts = ["Fira Code", "Source Code Pro", "Consolas",
                       "Monoid", "Ubuntu Mono", "JetBrains Mono", "Hack" ]

    font = QFont()  # creates a QFont object
    for pref_font in preferred_fonts:
        if pref_font in QFontDatabase().families():  # checks if the preferred font is installed
            font.setFamily(pref_font)
            logging.info(f"found font {pref_font}")
            break
    else:  # if none of the preferred fonts match exactly
        font.setFamily("Courier New")  # then set font to Courier New

    font.setPointSize(10)
    return font

def remove_ansi_color_codes(string: str) -> str:
    # ansi escape code pattern
    ansi_escape_pattern = re.compile(r'\x1b\[.*?[@-~]')
    return ansi_escape_pattern.sub('', string)