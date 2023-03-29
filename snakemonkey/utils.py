from html.parser import HTMLParser
from io import StringIO
from unicodedata import normalize


class HTMLRemover(HTMLParser):
    """Class for removing HTML tags from text."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_tags(text):
    """Removes HTML tags from text.

    Parameters
    ----------
    text : str
        Text containing HTML tags

    Returns
    -------
    str
        Text without HTML tags.

    """
    s = HTMLRemover()
    s.feed(text)
    return s.get_data()


def clean_column(col):
    new_col = normalize("NFKC", col)
    new_col = " ".join(new_col.split())
    return new_col
