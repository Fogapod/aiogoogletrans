class Translated(object):
    """Translate result object

    :param src: source language detected by google
    :param confidence: confidence of the detection
    :param dest: destination language (default: en)
    :param origin: original text
    :param text: translated text
    :param pronunciation: pronunciation
    """
    def __init__(self, src, confidence, dest, origin, text, pronunciation):
        self.src = src
        self.confidence = confidence
        self.dest = dest
        self.origin = origin
        self.text = text
        self.pronunciation = pronunciation

    def __str__(self):  # pragma: nocover
        return (
            f'Translated(src={self.src}, confidence={self.confidence}, dest={self.dest},'
            f'text={self.text}, pronunciation={self.pronunciation})'
        )
