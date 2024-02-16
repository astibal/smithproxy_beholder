HAVE_MARKDOWN = False
try:
    import markdown

    HAVE_MARKDOWN = True
except ImportError:
    pass
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from ui.static_text import S


class Text:
    Help_NoMarkdown = "<h3> python3-markdown not installed </h3>"

    class Help_ContentTab:
        markdown = S.md_content_help


class MarkdownViewer(QWidget):
    def __init__(self, parent=None):
        super(MarkdownViewer, self).__init__(parent)

        self.setWindowTitle("Smithproxy WebHook App HELP")
        self.textBrowser = QTextBrowser(self)
        font = QFont()
        font.setPointSize(12)
        self.textBrowser.setFont(font)

        layout = QVBoxLayout(self)
        layout.addWidget(self.textBrowser)
        self.setLayout(layout)
        self.setGeometry(200, 200, 800, 600)

    def setMarkdown(self, markdown_text):
        if not HAVE_MARKDOWN:
            self.textBrowser.setHtml(Text.Help_NoMarkdown)
            return

        html = markdown.markdown(markdown_text)
        self.textBrowser.setHtml(html)
