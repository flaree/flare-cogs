import html.parser
import re

__all__ = ["html_to_text"]

WhitespaceHandler = re.compile("<p>|<br>|<li>", flags=re.MULTILINE)

# The below is semi-safe for use here,
# wouldn't reccomend copying this without understanding it.
# html cleanup is taken from https://stackoverflow.com/a/7778368
# with some modifications made to better suit the needs of this.


class HTMLTextExtractor(html.parser.HTMLParser):  # https://stackoverflow.com/a/7778368
    def __init__(self):
        super().__init__()
        self.result = []

    def handle_data(self, d):
        self.result.append(d)

    def get_text(self):
        return "".join(self.result)


def html_to_text(html_data):  # https://stackoverflow.com/a/7778368
    """Converts HTML to plain text (stripping tags and converting entities).

    >>> html_to_text('<a href="#">Demo<!--...--> <em>(&not; \u0394&#x03b7;&#956;&#x03CE;)</em></a>')
    'Demo (\xac \u0394\u03b7\u03bc\u03ce)'
    "Plain text" doesn't mean result can safely be used as-is in HTML.
    >>> html_to_text('&lt;script&gt;alert("Hello");&lt;/script&gt;')
    '<script>alert("Hello");</script>'
    Always use html.escape to sanitize text before using in an HTML context!
    HTMLParser will do its best to make sense of invalid HTML.
    >>> html_to_text('x < y &lt z <!--b')
    'x < y < z '
    Unrecognized named entities are included as-is. '&apos;' is recognized,
    despite being XML only.
    >>> html_to_text('&nosuchentity; &apos; ')
    "&nosuchentity; ' "
    """
    html_data = WhitespaceHandler.sub("\n", html_data)
    s = HTMLTextExtractor()
    s.feed(html_data)
    return s.get_text()
