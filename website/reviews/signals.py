import blinker


signals = blinker.Namespace()
reviews_email = signals.signal('reviews_email')
