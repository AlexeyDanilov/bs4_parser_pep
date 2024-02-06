class ParserFindTagException(Exception):
    """Вызывается, когда парсер не может найти тег."""


class TextNotFoundException(Exception):
    """Вызывается, когда парсер не может найти текст в html-коде."""
